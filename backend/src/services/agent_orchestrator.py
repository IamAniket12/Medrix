"""
Multi-Agent Orchestrator for Medical Document Analysis using LangGraph.
Includes 4-agent pipeline:
- Agent 1: Document Validator
- Agent 2: Clinical Extractor
- Agent 3: Intelligent Summarizer
- Agent 6: Relationship Mapper (entity relationships)
"""

import asyncio
import warnings
from typing import Dict, Any, List, TypedDict, Annotated, Optional
from typing_extensions import TypedDict as ExtTypedDict
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field, validator
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Suppress SSL verification warnings for ngrok endpoints (development/testing)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
import operator
from sqlalchemy.orm import Session
from datetime import datetime
import json
from decimal import Decimal
import uuid
from typing import Literal

# Import agent services
from .relationship_mapper import relationship_mapper
from ..schemas.validation_schemas import (
    DetailedSummary,
    SummaryResponse,
)


def json_serializer(obj):
    """Helper to serialize datetime, date, and Decimal objects for JSON."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


# ============================================================
# PYDANTIC VALIDATION SCHEMAS (Priority 1)
# ============================================================


class ValidationResult(BaseModel):
    """Validated response from document validator agent."""

    is_valid: bool
    quality_score: float = Field(ge=0, le=1)
    issues: List[str] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    """Document metadata from validator."""

    document_type: str
    document_subtype: Optional[str] = None
    document_date: Optional[str] = None
    document_source: Optional[str] = None
    provider: Optional[Dict[str, Any]] = None


class ValidationResponse(BaseModel):
    """Complete validation agent response."""

    validation: ValidationResult
    document_metadata: DocumentMetadata
    processability: Dict[str, Any]


class ClinicalCondition(BaseModel):
    """Validated clinical condition."""

    name: str
    icd10_code: Optional[str] = None
    status: Optional[str] = None
    diagnosed_date: Optional[str] = None
    severity: Optional[str] = None
    body_site: Optional[str] = None


class ClinicalMedication(BaseModel):
    """Validated medication."""

    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    status: Optional[str] = "active"


class ClinicalDataResponse(BaseModel):
    """Complete clinical extraction response."""

    conditions: List[ClinicalCondition] = Field(default_factory=list)
    medications: List[ClinicalMedication] = Field(default_factory=list)
    allergies: List[Dict[str, Any]] = Field(default_factory=list)
    lab_results: List[Dict[str, Any]] = Field(default_factory=list)
    vital_signs: List[Dict[str, Any]] = Field(default_factory=list)
    procedures: List[Dict[str, Any]] = Field(default_factory=list)
    immunizations: List[Dict[str, Any]] = Field(default_factory=list)


# DetailedSummary and SummaryResponse are imported from validation_schemas above.
# They live in one canonical place so the orchestrator and persistence layer
# always agree on what fields (including search_optimized_summary) are required.


# ============================================================
# AGENT STATE
# ============================================================


class AgentState(ExtTypedDict):
    """State shared between agents."""

    image_bytes: bytes
    filename: str
    file_type: str

    # Progress tracking
    job_id: Optional[str]  # Unique job ID for progress tracking

    # Database and user context
    db_session: Optional[Any]  # Database session for relationship mapper
    user_id: Optional[str]  # User ID for relationship mapper
    document_id: Optional[int]  # Document ID being processed

    # Agent outputs
    validation: Dict[str, Any]  # Agent 1: Document Validator
    clinical_data: Dict[str, Any]  # Agent 2: Clinical Data Extractor
    summaries: Dict[str, Any]  # Agent 3: Intelligent Summarizer
    relationships: Dict[str, Any]  # Agent 6: Relationship Mapper

    # Validation gate
    is_valid: bool
    should_continue: bool
    needs_review: bool  # Always False (no verifier)

    errors: Annotated[List[str], operator.add]


class MedicalDocumentAgentOrchestrator:
    """Orchestrates multiple specialized agents for medical document analysis."""

    # Class-level progress tracking
    _progress_store: Dict[str, Dict[str, Any]] = {}

    def __init__(self, settings):
        """
        Initialize the agent orchestrator.

        Args:
            settings: Application settings
        """
        self.settings = settings

        # ── HTTP / Colab mode ──────────────────────────────────────────────
        # When MEDGEMMA_ENDPOINT_URL is set (e.g. a Colab + ngrok deployment),
        # all LLM calls go to that HTTP endpoint instead of Vertex AI.
        http_url = getattr(settings, "medgemma_endpoint_url", None)
        if http_url:
            self._mode = "http"
            self._http_url = http_url.rstrip("/")
            self.endpoint = None
            print(f"✓ AgentOrchestrator → HTTP / Colab mode: {self._http_url}")
        else:
            # ── Vertex AI mode (default) ───────────────────────────────────
            self._mode = "vertex"
            self._http_url = None
            from google.cloud import aiplatform

            self.endpoint = aiplatform.Endpoint(
                endpoint_name=f"projects/{settings.google_cloud_project}/locations/{settings.vertex_ai_location}/endpoints/{settings.medgemma_endpoint_id}"
            )

        # Build the agent graph
        self.graph = self._build_graph()

    @classmethod
    def update_progress(
        cls,
        job_id: str,
        stage: Literal[
            "validating", "extracting", "summarizing", "mapping", "completed", "failed"
        ],
        status: Literal["in_progress", "completed", "failed"],
        message: str = "",
        error: str = None,
    ):
        """Update progress for a document processing job."""
        if job_id not in cls._progress_store:
            cls._progress_store[job_id] = {
                "job_id": job_id,
                "started_at": datetime.utcnow().isoformat(),
                "stages": {
                    "validating": {"status": "pending", "message": ""},
                    "extracting": {"status": "pending", "message": ""},
                    "summarizing": {"status": "pending", "message": ""},
                    "mapping": {"status": "pending", "message": ""},
                },
                "current_stage": stage,
                "overall_status": "in_progress",
                "error": None,
            }
            print(f"[Progress] Created progress tracking for job: {job_id}")

        progress = cls._progress_store[job_id]

        # Handle special "completed" and "failed" stages (overall status only)
        if stage == "completed":
            progress["overall_status"] = "completed"
            progress["completed_at"] = datetime.utcnow().isoformat()
            # Set mapping as completed since it's the last real stage
            if "mapping" in progress["stages"]:
                progress["stages"]["mapping"]["status"] = "completed"
            print(f"[Progress] Job {job_id} marked as COMPLETED")
            return
        elif stage == "failed":
            progress["overall_status"] = "failed"
            progress["error"] = error
            print(f"[Progress] Job {job_id} marked as FAILED: {error}")
            return

        # Handle regular agent stages
        progress["current_stage"] = stage
        if stage in progress["stages"]:
            progress["stages"][stage]["status"] = status
            progress["stages"][stage]["message"] = message
            print(f"[Progress] Job {job_id} - Stage '{stage}' → {status}: {message}")

        if status == "failed":
            progress["overall_status"] = "failed"
            progress["error"] = error
        elif stage == "mapping" and status == "completed":
            progress["overall_status"] = "completed"
            progress["completed_at"] = datetime.utcnow().isoformat()
            print(f"[Progress] Job {job_id} all stages COMPLETED")

    @classmethod
    def create_job_id(cls, filename: str) -> str:
        """Generate a unique job ID for progress tracking."""
        import uuid

        job_id = f"{uuid.uuid4().hex[:8]}-{filename[:20].replace(' ', '_')}"
        return job_id

    @classmethod
    def get_progress(cls, job_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for a document processing job."""
        return cls._progress_store.get(job_id)

    def _build_graph(self):
        """
        Build the LangGraph agent workflow.

        Flow:
        1. Agent 1: Validator (quality gate)
        2. Agent 2: Clinical Extractor
        3. Agent 3: Intelligent Summarizer
        4. Agent 6: Relationship Mapper
        """
        workflow = StateGraph(AgentState)

        workflow.add_node("validator", self._document_validator)  # Agent 1
        workflow.add_node("extractor", self._clinical_extractor)  # Agent 2
        workflow.add_node("summarizer", self._intelligent_summarizer)  # Agent 3
        workflow.add_node("relationship_mapper", self._relationship_mapper)  # Agent 6

        workflow.set_entry_point("validator")

        # Validator → Extractor (or stop)
        workflow.add_conditional_edges(
            "validator",
            self._should_continue_processing,
            {"continue": "extractor", "stop": END},
        )

        # Sequential: Extractor → Summarizer → Relationship Mapper → END
        workflow.add_edge("extractor", "summarizer")
        workflow.add_edge("summarizer", "relationship_mapper")
        workflow.add_edge("relationship_mapper", END)

        return workflow.compile()

    def _should_continue_processing(self, state: AgentState) -> str:
        """Decide whether to continue processing after validation."""
        if state.get("is_valid", False) and state.get("should_continue", False):
            return "continue"
        return "stop"

    async def _document_validator(self, state: AgentState) -> Dict[str, Any]:
        """
        Agent 1: Document Validator
        Validates document quality and determines if it should be processed.
        """
        try:
            prompt = """Analyze this medical document image and respond with a JSON object.

The JSON must have EXACTLY this top-level structure (three keys: validation, document_metadata, processability):

{
  "validation": {
    "is_valid": <true if the document is a medical image or record, false otherwise>,
    "quality_score": <0.0 to 1.0 - readability/completeness>,
    "issues": <array of strings describing any problems, empty array if none>
  },
  "document_metadata": {
    "document_type": <one of: lab_report, prescription, x-ray, discharge_summary, consultation_note, imaging, other>,
    "document_subtype": <specific subtype string or null>,
    "document_date": <ISO date string "YYYY-MM-DD" or null>,
    "document_source": <hospital or clinic name or null>,
    "provider": {
      "name": <doctor name or null>,
      "specialty": <medical specialty or null>
    }
  },
  "processability": {
    "can_extract_text": <true if text is readable or image has diagnostic value>,
    "estimated_confidence": <0.0 to 1.0>,
    "language": <ISO 639-1 language code, e.g. "en">
  }
}

VALIDATION RULES:
- Set is_valid to TRUE for:
  - Medical imaging (X-rays, CT, MRI, ultrasound) - even without text labels
  - Lab reports and test results
  - Prescriptions and medication lists
  - Discharge summaries and consultation notes
  - Any document with medical/diagnostic value
  
- Set is_valid to FALSE ONLY if:
  - Image is completely blank or corrupted
  - Image is too blurry to see any anatomical structures or text
  - Image is clearly not medical-related (e.g., random photo, meme, advertisement)
  - Document is illegible and cannot provide any clinical value

For medical images without text (X-rays, scans):
- Set document_type to "x-ray" or "imaging"
- Set can_extract_text to false (no text to extract)
- Set estimated_confidence based on image clarity (0.7-0.9 for clear scans)
- Set quality_score based on diagnostic value (0.7-1.0 for clear medical images)
- Leave date/provider fields as null if not visible
- Issues array can note "No text labels visible" or "Limited metadata" but still accept

Output the JSON object and nothing else."""

            response = await self._call_llm_with_retry(
                prompt, state["image_bytes"], state["filename"]
            )

            print("\n" + "─" * 60)
            print("🔎 AGENT-1 RAW MODEL OUTPUT:")
            print("─" * 60)
            print(response)
            print("─" * 60 + "\n")

            validation_result = self._parse_and_validate_validation(response)

            is_valid = validation_result.get("validation", {}).get("is_valid", False)
            quality_score = validation_result.get("validation", {}).get(
                "quality_score", 0.0
            )
            should_continue = is_valid and quality_score >= 0.5

            # Update progress
            job_id = state.get("job_id")
            if job_id:
                if is_valid:
                    self.update_progress(
                        job_id,
                        "validating",
                        "completed",
                        f"Document validated (quality: {quality_score:.2f})",
                    )
                    self.update_progress(
                        job_id,
                        "extracting",
                        "in_progress",
                        "Extracting clinical data...",
                    )
                else:
                    issues = validation_result.get("validation", {}).get("issues", [])
                    self.update_progress(
                        job_id,
                        "validating",
                        "failed",
                        "Document validation failed",
                        error=", ".join(issues),
                    )

            if is_valid:
                print(f"✓ Document Validator: PASSED (quality: {quality_score:.2f})")
            else:
                issues = validation_result.get("validation", {}).get("issues", [])
                print(f"❌ Document Validator: FAILED — {', '.join(issues)}")

            return {
                "validation": validation_result,
                "is_valid": is_valid,
                "should_continue": should_continue,
            }

        except Exception as e:
            print(f"❌ Document Validator error: {e}")
            job_id = state.get("job_id")
            if job_id:
                self.update_progress(
                    job_id, "validating", "failed", "Validation error", error=str(e)
                )
            return {
                "validation": {"error": str(e)},
                "is_valid": False,
                "should_continue": False,
                "errors": [f"Validation: {str(e)}"],
            }

    async def _clinical_extractor(self, state: AgentState) -> Dict[str, Any]:
        """
        Agent 2: Clinical Data Extractor
        Extracts ALL structured medical data from the document.
        Operates solely on the document image - no prior patient history
        is injected to avoid anchoring bias.
        """
        try:
            prompt = """You are a clinical data transcription agent. Your only job is to copy information that is EXPLICITLY WRITTEN in the medical document into a JSON structure.

ABSOLUTE RULES — violations are worse than an empty array:
1. ONLY extract what is EXPLICITLY and LITERALLY written in the document. Nothing else.
2. DO NOT infer, assume, imply, or deduce anything not directly stated in the document.
3. DO NOT diagnose. A symptom or complaint (e.g. "fatigue", "leg swelling") is NOT a condition unless the document explicitly states it as a diagnosis or active problem.
4. DO NOT add medications that are not explicitly prescribed or listed in this document.
5. DO NOT populate a field by reasoning about what "must" be present. If it is not written, it does not exist.
6. DO NOT use the example values in the JSON template below as hints for what to extract — they are FORMAT EXAMPLES ONLY.
7. Use null for any field not explicitly stated. Use [] for any category with no documented entries in this document.

WHAT TO INCLUDE (only if explicitly written):
- conditions: Diagnoses or active problems the document explicitly names (e.g. "Dx: Hypertension", "Assessment: T2DM"). NOT symptoms unless labeled as a diagnosis.
- medications: Drugs explicitly prescribed, dispensed, or listed in the document with their written details.
- allergies: Allergies or adverse reactions explicitly documented by name.
- lab_results: Lab tests explicitly ordered or resulted in this document. Use "pending" as value only if the document says it is ordered/pending.
- vital_signs: Vital sign values explicitly recorded with their numbers.
- procedures: Procedures explicitly stated as performed or ordered in this document.
- immunizations: Vaccines explicitly documented in this document.

Output ONLY this JSON structure. Use [] for categories with no data. Output no markdown, no explanation, no commentary.

{
  "conditions": [
    {"name": "<condition exactly as written>", "icd10_code": null, "status": "<active/resolved/chronic — ONLY if explicitly stated, else null>", "diagnosed_date": null, "severity": null, "body_site": null}
  ],
  "medications": [
    {"name": "<drug name exactly as written>", "dosage": "<as written or null>", "frequency": "<as written or null>", "route": "<as written or null>", "status": "active", "prescriber": null, "instructions": "<as written or null>"}
  ],
  "allergies": [
    {"allergen": "<as written>", "allergen_type": "<only if stated>", "reaction": "<as written or null>", "severity": "<as written or null>"}
  ],
  "lab_results": [
    {"test_name": "<as written>", "value": "<result value or 'pending' if ordered>", "unit": "<as written or null>", "reference_range": null, "is_abnormal": false, "test_date": null}
  ],
  "vital_signs": [
    {"type": "<vital type>", "value": null, "unit": "<as written>", "systolic": null, "diastolic": null, "measured_date": null}
  ],
  "procedures": [
    {"procedure_name": "<as written>", "performed_date": null, "outcome": null}
  ],
  "immunizations": [
    {"vaccine_name": "<as written>", "administered_date": null}
  ]
}

Now read the document image and output ONLY the JSON object populated with information that is EXPLICITLY WRITTEN in this document."""

            response = await self._call_llm_with_retry(
                prompt, state["image_bytes"], state["filename"]
            )

            # Log raw response for debugging
            print("\n" + "─" * 70)
            print("🔎 AGENT-2 RAW MODEL OUTPUT:")
            print("─" * 70)
            print(response)  # Full response, no truncation
            print("─" * 70)
            print(f"Response length: {len(response)} chars\n")

            clinical_data = self._parse_and_validate_clinical_data(response)

            counts = {
                k: len(v) for k, v in clinical_data.items() if isinstance(v, list)
            }
            print(f"✓ Clinical Data Extractor: {counts}")

            # Update progress
            job_id = state.get("job_id")
            if job_id:
                self.update_progress(
                    job_id,
                    "extracting",
                    "completed",
                    f"Extracted {sum(counts.values())} clinical items",
                )
                self.update_progress(
                    job_id,
                    "summarizing",
                    "in_progress",
                    "Creating document summaries...",
                )

            return {"clinical_data": clinical_data}

        except Exception as e:
            print(f"❌ Clinical Data Extractor error: {e}")
            job_id = state.get("job_id")
            if job_id:
                self.update_progress(
                    job_id, "extracting", "failed", "Extraction error", error=str(e)
                )
            return {
                "clinical_data": {"error": str(e)},
                "errors": [f"Clinical Extraction: {str(e)}"],
            }

    async def _intelligent_summarizer(self, state: AgentState) -> Dict[str, Any]:
        """
        Agent 3: Intelligent Summarizer
        Creates summaries for BOTH humans and future AI agents.
        """
        try:
            prompt = """Summarize this medical document image. Produce TWO distinct summaries.

Return a JSON object with EXACTLY these five top-level keys:
  brief_summary, search_optimized_summary, urgency_level, detailed_summary, agent_context

CRITICAL JSON FORMATTING RULES:
- Use empty arrays [] (not null) for any list fields with no data (e.g., key_findings, action_items, risk_factors)
- Use empty strings "" (not null) for any string fields with no data
- Use empty objects {} (not null) for any object fields with no data
- Never use null values in the JSON output

KEY DEFINITIONS:

brief_summary (string):
  5-7 complete sentences written for a clinician or patient.
  Cover: who the patient is, what brought them in, key diagnoses/conditions,
  current medications or treatments, important lab/vital findings, and next steps.
  Minimum 150 words. Must NOT be a bullet list - write flowing prose.

search_optimized_summary (string):
  400-600 word dense paragraph written to maximise semantic search recall.
  Include ALL of the following that appear in the document:
  - Full condition names AND their abbreviations (e.g. "Type 2 Diabetes Mellitus (T2DM, DM2)")
  - Every medication with dosage and route
  - Every lab test name, value, unit, and whether abnormal
  - Every vital sign with exact numbers
  - Symptoms, complaints, body sites
  - Procedures, diagnoses, ICD-10 codes if visible
  - Provider names, facility, visit date
  - Action items, follow-up instructions
  Write as connected prose - NO bullet points. Repeat key terms naturally.
  This text will be embedded for vector search so exhaustive terminology coverage is critical.

urgency_level (string): exactly one of: routine | follow-up-needed | urgent | critical

detailed_summary (object):
  clinical_overview (string), key_findings (array of strings - use [] if none),
  treatment_plan (object: medications_started, medications_stopped, lifestyle_modifications, follow_up - use "" or [] for empty fields),
  clinical_significance (string), action_items (array of strings - use [] if none)

agent_context (object):
  document_purpose (string), clinical_domain (string), completeness_score (0.0-1.0),
  semantic_keywords (array of strings - use [] if none),
  temporal_events: array of {event_type, event_title, event_description, date, importance, provider, facility, related_entity} - use [] if none,
  risk_factors (array of strings - use [] if none), missing_information (array of strings - use [] if none),
  recommendations_for_future_agents: {timeline_agent, risk_agent, search_agent}

Output the JSON object and nothing else."""

            response = await self._call_llm_with_retry(
                prompt, state["image_bytes"], state["filename"]
            )

            # Log raw response for debugging
            print("\n" + "─" * 70)
            print("🔎 AGENT-3 RAW MODEL OUTPUT:")
            print("─" * 70)
            print(response)  # Full response, no truncation
            print("─" * 70)
            print(f"Response length: {len(response)} chars\n")

            summaries = self._parse_and_validate_summary(response)

            urgency = summaries.get("urgency_level", "routine")
            brief = (summaries.get("brief_summary", "") or "")[:100]
            print(f"✓ Intelligent Summarizer: {urgency.upper()}")
            print(f"  Summary: {brief}...")

            # Update progress
            job_id = state.get("job_id")
            if job_id:
                self.update_progress(
                    job_id,
                    "summarizing",
                    "completed",
                    f"Summary created ({urgency} urgency)",
                )
                self.update_progress(
                    job_id, "mapping", "in_progress", "Mapping relationships..."
                )

            return {"summaries": summaries}

        except Exception as e:
            print(f"❌ Intelligent Summarizer error: {e}")
            job_id = state.get("job_id")
            if job_id:
                self.update_progress(
                    job_id, "summarizing", "failed", "Summarization error", error=str(e)
                )
            return {
                "summaries": {
                    "brief_summary": "Error processing summary",
                    "search_optimized_summary": "Summary extraction failed — embeddings unavailable for this document.",
                    "urgency_level": "routine",
                    "detailed_summary": {},
                    "agent_context": {},
                    "error": str(e),
                },
                "errors": [f"Summarization: {str(e)}"],
            }

    async def _relationship_mapper(self, state: AgentState) -> Dict[str, Any]:
        """
        Agent 6: Relationship Mapper
        Maps relationships between clinical entities (medications to conditions, labs to conditions, etc.)
        """
        try:
            print(f"🔍 Agent 6: Relationship Mapper")

            # Get database session and user ID
            db_session = state.get("db_session")
            user_id = state.get("user_id")
            document_id = state.get("document_id")

            if not db_session or not user_id:
                print(
                    "⚠️  No database session or user ID - skipping relationship mapping"
                )
                return {
                    "relationships": {
                        "relationships": [],
                        "summary": {},
                        "total_count": 0,
                    }
                }

            # Map relationships
            relationships = relationship_mapper.map_all_relationships(
                db=db_session, user_id=user_id, document_id=document_id
            )

            print(
                f"✓ Relationship Mapper: Found {relationships['total_count']} relationships"
            )
            if relationships["summary"]:
                print(f"  By type: {relationships['summary'].get('by_type', {})}")

            # Update progress - this is the final stage
            job_id = state.get("job_id")
            if job_id:
                self.update_progress(
                    job_id,
                    "mapping",
                    "completed",
                    f"Mapped {relationships['total_count']} relationships",
                )

            return {"relationships": relationships}

        except Exception as e:
            print(f"❌ Relationship Mapper error: {e}")
            job_id = state.get("job_id")
            if job_id:
                self.update_progress(
                    job_id,
                    "mapping",
                    "failed",
                    "Relationship mapping error",
                    error=str(e),
                )
            return {
                "relationships": {
                    "error": str(e),
                    "relationships": [],
                    "summary": {},
                    "total_count": 0,
                },
                "errors": [f"Relationship Mapping: {str(e)}"],
            }

    # ============================================================
    # Priority 2: RETRY LOGIC WITH TENACITY
    # ============================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    async def _call_llm_with_retry(
        self, prompt: str, image_bytes: bytes, filename: str
    ) -> str:
        """
        Call LLM with automatic retry logic.
        Retries up to 3 times with exponential backoff on network errors.
        Strips MedGemma-1.5 thinking tokens (<unused94>...<unused95>) from
        every response so all downstream parsers receive clean output.
        """
        import re

        raw = await self._call_llm(prompt, image_bytes, filename)
        # Remove full thinking blocks:  <unusedN> ... <unusedN>
        clean = re.sub(r"<unused\d+>.*?<unused\d+>\s*", "", raw, flags=re.DOTALL)
        # Remove any stray remaining tokens
        clean = re.sub(r"<unused\d+>", "", clean).strip()
        if clean != raw:
            print(
                f"  ↳ Stripped thinking tokens ({len(raw) - len(clean)} chars removed)"
            )
        return clean

    def _prepare_image(self, image_bytes: bytes, filename: str) -> tuple[bytes, str]:
        """
        Prepare an image for the MedGemma endpoint.

        For Vertex AI: 1.5 MB total request limit - target 1,050 KB raw bytes
        For Colab/HTTP: More flexible limits (T4 GPU with 16GB VRAM) - target 2,500 KB raw bytes

        Strategy - quality first, dimensions last:
          1. If already under budget, return as-is.
          2. Cap the image at 2560px (Colab) or 1920px (Vertex) on longest side.
          3. Binary-search JPEG quality from 92 to 72 in steps of 4.
          4. If quality-only compression is not enough, reduce dimensions in
             steps (for Colab: 2048 to 1600 to 1280; for Vertex: 1600 to 1280 to 1024 to 896).
          5. Absolute last resort: 896x896 / q=65.

        Returns (prepared_bytes, mime_type).
        """
        from PIL import Image
        import io

        # Only compress images larger than 1.5MB
        # Both Colab (T4 GPU) and Vertex AI can handle 1.5MB images efficiently
        # This preserves original quality for most medical documents
        TARGET_BYTES = 1_500_000  # 1.5 MB threshold
        MAX_INITIAL_DIM = 1920
        FALLBACK_DIMS = [1600, 1280, 1024, 896]

        QUALITY_HIGH = 92
        QUALITY_LOW = 72
        QUALITY_STEP = 4

        ext = filename.lower()
        mime = (
            "image/jpeg"
            if (ext.endswith(".jpg") or ext.endswith(".jpeg"))
            else "image/png" if ext.endswith(".png") else "image/jpeg"
        )
        original_size = len(image_bytes)

        # ── FAST PATH: Image is already small, send as-is ──────────────────
        # CRITICAL: Do NOT re-encode images that are already under budget!
        # Re-encoding can introduce JPEG artifacts, strip EXIF rotation data,
        # and actually make the image look WORSE to the model.
        if original_size <= TARGET_BYTES:
            # Quick validation: can PIL open it without errors?
            try:
                img_test = Image.open(io.BytesIO(image_bytes))
                img_test.verify()  # Check if image is valid
                print(
                    f"  ✓ Image {original_size // 1024} KB already under budget — sending original"
                )
                return image_bytes, mime
            except Exception as e:
                # Image is corrupted, need to normalize it through PIL
                print(f"  ⚠️  Image validation failed ({e}) — normalizing through PIL")
                # Fall through to normalization logic

        # ── Normalization needed: re-encode through PIL ────────────────────
        try:
            img = Image.open(io.BytesIO(image_bytes))

            # Normalize color mode: always convert to RGB (except grayscale)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            orig_w, orig_h = img.size

            # If we're here, the image was either over budget or corrupted
            if original_size > TARGET_BYTES:
                print(
                    f"⚙️  Image {original_size / 1024 / 1024:.2f} MB — fitting to "
                    f"target ≤ {TARGET_BYTES // 1024} KB"
                )
            else:
                print(
                    f"⚙️  Image {original_size / 1024 / 1024:.2f} MB — fitting to "
                    f"target ≤ {TARGET_BYTES // 1024} KB"
                )

            # Image is over budget or corrupted — compress it
            def _try_compress(pil_img: Image.Image, quality: int) -> bytes:
                buf = io.BytesIO()
                pil_img.save(
                    buf, format="JPEG", quality=quality, optimize=True, progressive=True
                )
                return buf.getvalue()

            def _resize_to(pil_img: Image.Image, max_dim: int) -> Image.Image:
                """Resize so the longest side equals max_dim (aspect-ratio preserved)."""
                w, h = pil_img.size
                if max(w, h) <= max_dim:
                    return pil_img
                scale = max_dim / max(w, h)
                return pil_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

            def _binary_search_quality(pil_img: Image.Image) -> bytes | None:
                """
                Find the highest JPEG quality where the output fits TARGET_BYTES.
                Returns the compressed bytes, or None if even QUALITY_LOW is too large.
                """
                lo, hi = QUALITY_LOW, QUALITY_HIGH
                best: bytes | None = None
                # Try high quality first for early exit
                candidate = _try_compress(pil_img, QUALITY_HIGH)
                if len(candidate) <= TARGET_BYTES:
                    return candidate
                # Linear descent in steps — fast enough for 5 iterations
                for q in range(
                    QUALITY_HIGH - QUALITY_STEP, QUALITY_LOW - 1, -QUALITY_STEP
                ):
                    candidate = _try_compress(pil_img, q)
                    if len(candidate) <= TARGET_BYTES:
                        return candidate
                return None

            # ── Pass 1: cap at MAX_INITIAL_DIM, binary-search quality ───────
            working = _resize_to(img, MAX_INITIAL_DIM)
            if working.size != (orig_w, orig_h):
                print(
                    f"  ↳ Capped to {working.size[0]}×{working.size[1]} (longest side ≤ {MAX_INITIAL_DIM}px)"
                )

            result = _binary_search_quality(working)
            if result:
                print(
                    f"  ✓ {orig_w}×{orig_h} → {working.size[0]}×{working.size[1]}  "
                    f"{original_size // 1024} KB → {len(result) // 1024} KB"
                )
                return result, "image/jpeg"

            # ── Pass 2: progressive dimension reduction ──────────────────────
            for max_dim in FALLBACK_DIMS:
                if max_dim >= max(working.size):
                    continue  # already smaller, skip
                shrunk = _resize_to(img, max_dim)
                result = _binary_search_quality(shrunk)
                if result:
                    print(
                        f"  ✓ {orig_w}×{orig_h} → {shrunk.size[0]}×{shrunk.size[1]}  "
                        f"{original_size // 1024} KB → {len(result) // 1024} KB"
                    )
                    return result, "image/jpeg"
                print(
                    f"  ↳ {shrunk.size[0]}×{shrunk.size[1]} still too large — reducing further"
                )

            # ── Absolute last resort ─────────────────────────────────────────
            final = _resize_to(img, 896)
            result = _try_compress(final, 65)
            print(
                f"  ⚠️  Last resort: {final.size[0]}×{final.size[1]} q=65 → "
                f"{len(result) // 1024} KB (sending best effort)"
            )
            return result, "image/jpeg"

        except Exception as e:
            print(f"  ⚠️  Image preparation failed ({e}) — sending original")
            return image_bytes, mime

    async def _call_llm(self, prompt: str, image_bytes: bytes, filename: str) -> str:
        """
        Call the MedGemma LLM endpoint with image bytes.
        Uses chat completions format with base64 data URL.

        MedGemma 27B is built on Gemma 3 and uses inference-time compute
        (thinking tokens). We disable thinking at the request level so the
        model emits only the JSON answer. If the endpoint ignores that flag,
        _parse_json_response handles the thought block gracefully.

        Vertex AI enforces a 1.5 MB request size limit. Images are
        automatically resized/recompressed by _prepare_image before encoding.

        Args:
            prompt: The prompt for the LLM
            image_bytes: Raw image bytes
            filename: Original filename (to detect mime type)

        Returns:
            Raw LLM response string — NO stripping done here.
            All JSON extraction is centralized in _parse_json_response.
        """
        import base64

        try:
            # Same image preparation for both HTTP and Vertex AI:
            # _prepare_image normalises the image to RGB, detects mime type,
            # and only compresses if the image exceeds the Vertex AI size budget.
            # For images already under budget (fast path), it returns the
            # original bytes unchanged — so there is zero quality loss for
            # normal-sized uploads regardless of which endpoint is used.
            image_bytes, mime_type = self._prepare_image(image_bytes, filename)

            # Base64 encode and build data URL
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            data_url = f"data:{mime_type};base64,{image_b64}"
            print(
                f"✓ Data URL created: {len(image_bytes)} bytes → {len(data_url)} chars ({len(data_url)/1024/1024:.2f} MB)"
            )

            # ----------------------------------------------------------------
            # Build the chat completions request.
            # "thinking": {"type": "disabled"} tells Gemma 3 / MedGemma 27B
            # to skip internal reasoning tokens and output the answer directly.
            # If the deployed serving version does not support this flag it is
            # silently ignored, and _parse_json_response strips the thought
            # block as a fallback.
            # ----------------------------------------------------------------
            instances = [
                {
                    "@requestFormat": "chatCompletions",
                    "messages": [
                        {
                            "role": "system",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "You are a medical AI assistant. "
                                        "Your ONLY output must be a single, valid JSON object. "
                                        "Do NOT include any explanations, reasoning, markdown "
                                        "formatting, code fences, or additional text. "
                                        "Output the JSON object and nothing else."
                                    ),
                                }
                            ],
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        },
                    ],
                    # Disable thinking tokens at the request level.
                    # Gemma 3 / MedGemma respects this flag when the serving
                    # stack supports it (e.g., Vertex AI Model Garden ≥ v1.3).
                    "thinking": {"type": "disabled"},
                    "max_tokens": 8192,
                    "temperature": 0.0,
                }
            ]

            print(f"🔍 Calling MedGemma endpoint...")

            # ── Route: HTTP / Colab ────────────────────────────────────────
            if self._mode == "http":
                import httpx

                # ── Payload debug ──────────────────────────────────────────
                msgs = instances[0].get("messages", [])
                for m in msgs:
                    for p in m.get("content") or []:
                        if isinstance(p, dict):
                            if p.get("type") == "image_url":
                                url_val = p.get("image_url", {}).get("url", "")
                                print(
                                    f"  📦 Payload image_url: present={bool(url_val)}, len={len(url_val)}, prefix={url_val[:50]}..."
                                )
                            elif p.get("type") == "text":
                                text_len = len(p.get("text", ""))
                                print(f"  📦 Payload text ({text_len} chars)")
                # ── End payload debug ──────────────────────────────────────

                try:
                    # Disable SSL verification for ngrok endpoints (they can have certificate issues)
                    # This is safe for ngrok development/testing environments
                    import ssl

                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                    async with httpx.AsyncClient(
                        timeout=900.0,  # 15 min timeout for HPC (large outputs with max_tokens=8192)
                        verify=False,  # Disable SSL verification for ngrok
                    ) as client:
                        print(f"  → Sending request to {self._http_url}/predict")
                        resp = await client.post(
                            f"{self._http_url}/predict",
                            json={"instances": instances},
                            headers={
                                "Content-Type": "application/json",
                                # Required to bypass ngrok's browser-warning splash page
                                "ngrok-skip-browser-warning": "true",
                            },
                        )

                    print(f"  ← Response status: {resp.status_code}")

                    if resp.status_code != 200:
                        error_detail = resp.text[:500]
                        print(f"❌ HTTP Error {resp.status_code}: {error_detail}")
                        return f'{{"error": "HTTP {resp.status_code}: {error_detail}"}}'

                    data = resp.json()
                    predictions = data.get("predictions", [])
                    print(f"📥 HTTP predictions count: {len(predictions)}")

                    # Extract assistant content from chatCompletions response
                    if not predictions:
                        print("⚠️  No predictions in response")
                        return '{"error": "No predictions in HTTP response"}'

                    first = predictions[0]
                    print(f"  📦 First prediction type: {type(first)}")

                    if isinstance(first, dict):
                        # Check for error in prediction
                        if "error" in first:
                            error_msg = first["error"]
                            print(f"❌ Prediction error: {error_msg}")
                            return json.dumps(first)

                        # Try chatCompletions format first
                        choices = first.get("choices", [])
                        if choices:
                            content = choices[0].get("message", {}).get("content")
                            if content:
                                print(
                                    f"✓ Extracted from choices[0].message.content ({len(content)} chars)"
                                )
                                return content

                        # Fallback: try direct content/text keys
                        content = first.get("content") or first.get("text")
                        if content:
                            print(f"✓ Extracted from direct key ({len(content)} chars)")
                            return content

                        # If nothing found, log the structure
                        print(
                            f"⚠️  Unexpected response structure. Keys: {list(first.keys())}"
                        )

                    return json.dumps(first)

                except httpx.TimeoutException as e:
                    print(f"❌ HTTP timeout: {e}")
                    print(
                        "\n⏱️  REQUEST TIMEOUT - The HPC server took too long to respond"
                    )
                    print(
                        "This usually means the model is processing a very complex document"
                    )
                    print(
                        "or the server is overloaded. Try again or increase timeout.\n"
                    )
                    return '{"error": "Request timeout - HPC endpoint may be overloaded or the document is too complex"}'
                except httpx.ConnectError as e:
                    print(f"❌ HTTP connection error: {e}")
                    print("\n" + "=" * 70)
                    print("🔴 CONNECTION ERROR - CANNOT REACH HPC SERVER")
                    print("=" * 70)
                    print(f"Attempted to connect to: {self._http_url}")
                    print("\nPossible causes:")
                    print("  - HPC server is not running")
                    print("  - ngrok tunnel has expired")
                    print("  - Wrong URL in .env file")
                    print("  - Network/firewall blocking connection")
                    print("\nACTION REQUIRED:")
                    print("  1. Check if hpc_medgemma_server.py is running on HPC")
                    print("  2. Restart it: python hpc_medgemma_server.py")
                    print("  3. Copy the new ngrok URL")
                    print("  4. Update MEDGEMMA_ENDPOINT_URL in .env")
                    print("  5. Restart this backend")
                    print("=" * 70 + "\n")
                    return '{"error": "Connection failed - HPC server unreachable. Check if server is running and ngrok URL is current."}'
                except httpx.RequestError as e:
                    print(f"❌ HTTP request error: {e}")
                    return f'{{"error": "Connection failed: {str(e)}"}}'
                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ HTTP unexpected error: {error_msg}")

                    # Check for SSL errors
                    if "SSL" in error_msg or "ssl" in error_msg:
                        print("\n" + "=" * 70)
                        print("🔴 SSL ERROR - NGROK TUNNEL ISSUE")
                        print("=" * 70)
                        print("Your HPC server or ngrok tunnel may have:")
                        print("  1. Expired (free ngrok sessions expire after 2 hours)")
                        print("  2. Been restarted with a new URL")
                        print("  3. Stopped running")
                        print("\nACTION REQUIRED:")
                        print(
                            "  1. Check if hpc_medgemma_server.py is still running on HPC"
                        )
                        print("  2. If not, restart it: python hpc_medgemma_server.py")
                        print("  3. Copy the new ngrok URL from the output")
                        print("  4. Update MEDGEMMA_ENDPOINT_URL in your .env file")
                        print("  5. Restart this backend server")
                        print("=" * 70 + "\n")
                        return '{"error": "SSL Error - ngrok tunnel expired or unavailable. Check HPC server and restart with new ngrok URL."}'

                    import traceback

                    traceback.print_exc()
                    return f'{{"error": "HTTP call failed: {error_msg}"}}'

            # ── Route: Vertex AI ───────────────────────────────────────────
            response = self.endpoint.predict(instances=instances)

            predictions = response.predictions
            print(f"📥 Response predictions type: {type(predictions)}")

            # --- Error guard ---
            if isinstance(predictions, dict) and "error" in predictions:
                error_msg = predictions["error"].get(
                    "message", str(predictions["error"])
                )
                print(f"❌ MedGemma returned error: {error_msg}")
                return f'{{"error": "{error_msg}"}}'

            # --- Unpack predictions ---
            if isinstance(predictions, dict):
                result = predictions
            elif isinstance(predictions, list) and len(predictions) > 0:
                result = predictions[0]
            else:
                return '{"error": "No predictions in response"}'

            # Vertex AI sometimes double-nests: predictions = [[{...}]]
            # Unpack one more level if needed.
            if isinstance(result, list) and len(result) > 0:
                result = result[0]

            print(f"📥 Result type: {type(result)}")

            # --- Extract content string from response envelope ---
            # MedGemma on Vertex AI can nest the answer in several locations
            # depending on the serving version. Try each in priority order and
            # return the raw string — no stripping here.
            if isinstance(result, dict):
                content = (
                    result.get("content")
                    or result.get("text")
                    or (result.get("message") or {}).get("content")
                    or ((result.get("choices") or [{}])[0].get("message") or {}).get(
                        "content"
                    )
                )
                if content and isinstance(content, str):
                    print(f"✓ Extracted content from response ({len(content)} chars)")
                    return content

                # No recognized field — serialize the whole dict so
                # _parse_json_response can attempt recovery
                print(f"⚠️  No content field found. Keys: {list(result.keys())}")
                return json.dumps(result)

            # Last resort — should never reach here after the list unpack above
            print(f"⚠️  Unexpected result type {type(result)}, converting to string")
            return str(result)

        except Exception as e:
            print(f"❌ LLM call failed: {e}")
            import traceback

            traceback.print_exc()
            return f'{{"error": "LLM call failed: {str(e)}"}}'

    # ============================================================
    # Priority 1: VALIDATION METHODS
    # ============================================================

    def _parse_and_validate_summary(self, response: str) -> Dict[str, Any]:
        """
        Parse and validate summarizer (Agent 3) response.

        Tries strict Pydantic validation first; falls back to a lenient
        reshape so a partially-correct response doesn't fail the pipeline.
        """
        raw_data = self._parse_json_response(response)

        # --- Strict path ---
        try:
            return SummaryResponse(**raw_data).dict()
        except Exception as strict_err:
            print(f"⚠️  Summary strict validation failed: {strict_err}")

        # --- Lenient reshape: build a valid SummaryResponse from whatever
        #     fields are present in raw_data. ---
        try:
            brief = (
                raw_data.get("brief_summary")
                or raw_data.get("summary")
                or raw_data.get("clinical_overview")
                or "Document processed — summary unavailable"
            )
            # search_optimized_summary: fall back to brief if not provided
            search_opt = (
                raw_data.get("search_optimized_summary")
                or raw_data.get("search_summary")
                or str(brief)
            )
            urgency = raw_data.get("urgency_level", "routine")
            if urgency not in ("routine", "follow-up-needed", "urgent", "critical"):
                urgency = "routine"

            detail_raw = raw_data.get("detailed_summary", {}) or {}
            detail = DetailedSummary(
                clinical_overview=detail_raw.get("clinical_overview", ""),
                key_findings=detail_raw.get("key_findings", []),
                treatment_plan=detail_raw.get("treatment_plan", {}),
                clinical_significance=detail_raw.get("clinical_significance", ""),
                action_items=detail_raw.get("action_items", []),
            )
            result = SummaryResponse(
                brief_summary=str(brief),
                search_optimized_summary=str(search_opt),
                urgency_level=urgency,
                detailed_summary=detail,
                agent_context=raw_data.get("agent_context", {}),
            )
            print(f"  ✓ Summary lenient reshape succeeded")
            return result.dict()
        except Exception as lenient_err:
            print(f"⚠️  Summary lenient reshape also failed: {lenient_err}")

        # --- Hard fallback ---
        return {
            "brief_summary": "Summary unavailable — parsing error",
            "search_optimized_summary": "Summary extraction failed — embeddings unavailable for this document.",
            "urgency_level": "routine",
            "detailed_summary": {
                "clinical_overview": "",
                "key_findings": [],
                "treatment_plan": {},
                "clinical_significance": "",
                "action_items": [],
            },
            "agent_context": {},
        }

    def _parse_and_validate_clinical_data(self, response: str) -> Dict[str, Any]:
        """
        Parse and validate clinical extractor (Agent 2) response.

        Accepts both the full schema and a flat dict with top-level arrays.
        Individual list items that fail Pydantic are dropped rather than
        failing the whole extraction.
        """
        raw_data = self._parse_json_response(response)

        # --- Strict path ---
        try:
            return ClinicalDataResponse(**raw_data).dict()
        except Exception as strict_err:
            print(f"⚠️  Clinical data strict validation failed: {strict_err}")

        # --- Lenient path: validate item by item, drop invalid ones ---
        def safe_list(key, model_cls):
            items = raw_data.get(key, []) or []
            valid = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                try:
                    valid.append(model_cls(**item).dict())
                except Exception:
                    # Keep raw dict if Pydantic rejects it — better than losing data
                    valid.append(item)
            return valid

        try:
            result = {
                "conditions": safe_list("conditions", ClinicalCondition),
                "medications": safe_list("medications", ClinicalMedication),
                "allergies": raw_data.get("allergies", []) or [],
                "lab_results": raw_data.get("lab_results", []) or [],
                "vital_signs": raw_data.get("vital_signs", []) or [],
                "procedures": raw_data.get("procedures", []) or [],
                "immunizations": raw_data.get("immunizations", []) or [],
            }
            print(f"  ✓ Clinical data lenient reshape succeeded")
            return result
        except Exception as lenient_err:
            print(f"⚠️  Clinical data lenient reshape failed: {lenient_err}")

        # --- Hard fallback ---
        return {
            "conditions": [],
            "medications": [],
            "allergies": [],
            "lab_results": [],
            "vital_signs": [],
            "procedures": [],
            "immunizations": [],
        }

    def _parse_and_validate_validation(self, response: str) -> Dict[str, Any]:
        """
        Parse and validate the document validator (Agent 1) response.

        Handles two model output shapes:
          A) Fully nested (expected):
             {"validation": {...}, "document_metadata": {...}, "processability": {...}}
          B) Flat (model skipped outer wrapper):
             {"is_valid": true, "quality_score": 0.85, ...}

        Tries strict Pydantic → lenient reshape → hard fallback.
        Only marks the document invalid when the response literally contains
        an error or has data that implies invalidity.  A parse failure alone
        does NOT auto-reject valid medical documents.
        """
        raw_data = self._parse_json_response(response)

        # --- Guard: parser returned an error dict ---
        if "error" in raw_data and len(raw_data) <= 2:
            print(f"⚠️  Validation parse returned error: {raw_data.get('error')}")
            return self._validation_hard_fallback(
                f"JSON parse error: {raw_data.get('error')}"
            )

        # --- Strict path ---
        try:
            return ValidationResponse(**raw_data).dict()
        except Exception as strict_err:
            print(f"⚠️  Validation strict Pydantic failed: {strict_err}")

        # --- Lenient reshape: handle flat response (Shape B) ---
        # Detect Shape B: top-level keys are from the inner validation object
        flat_keys = {"is_valid", "quality_score", "issues"}
        if flat_keys.intersection(raw_data.keys()):
            print(f"  ↳ Detected flat validation response — reshaping to nested form")
            raw_data = {
                "validation": {
                    "is_valid": raw_data.get("is_valid", True),
                    "quality_score": raw_data.get("quality_score", 0.8),
                    "issues": raw_data.get("issues", []),
                },
                "document_metadata": raw_data.get(
                    "document_metadata",
                    {
                        "document_type": raw_data.get("document_type", "unknown"),
                        "document_subtype": raw_data.get("document_subtype"),
                        "document_date": raw_data.get("document_date"),
                        "document_source": raw_data.get("document_source"),
                        "provider": raw_data.get("provider"),
                    },
                ),
                "processability": raw_data.get(
                    "processability",
                    {
                        "can_extract_text": True,
                        "estimated_confidence": raw_data.get(
                            "estimated_confidence", 0.8
                        ),
                        "language": "en",
                    },
                ),
            }
            try:
                result = ValidationResponse(**raw_data).dict()
                print(f"  ✓ Validation reshape succeeded")
                return result
            except Exception as reshape_err:
                print(f"  ⚠️  Validation reshape Pydantic still failed: {reshape_err}")

        # --- Lenient path: build from whatever fields exist ---
        try:
            val_block = raw_data.get("validation", {}) or {}
            meta_block = raw_data.get("document_metadata", {}) or {}
            proc_block = raw_data.get("processability", {}) or {}

            result = ValidationResponse(
                validation=ValidationResult(
                    is_valid=bool(val_block.get("is_valid", True)),
                    quality_score=float(val_block.get("quality_score", 0.75)),
                    issues=val_block.get("issues", []) or [],
                ),
                document_metadata=DocumentMetadata(
                    document_type=meta_block.get("document_type", "unknown")
                    or "unknown",
                    document_subtype=meta_block.get("document_subtype"),
                    document_date=meta_block.get("document_date"),
                    document_source=meta_block.get("document_source"),
                    provider=meta_block.get("provider"),
                ),
                processability={
                    "can_extract_text": proc_block.get("can_extract_text", True),
                    "estimated_confidence": proc_block.get(
                        "estimated_confidence", 0.75
                    ),
                    "language": proc_block.get("language", "en"),
                },
            )
            print(f"  ✓ Validation lenient build succeeded")
            return result.dict()
        except Exception as lenient_err:
            print(f"⚠️  Validation lenient build also failed: {lenient_err}")

        # --- Hard fallback: assume document IS valid so we don't drop real
        #     medical records due to a transient parsing issue. ---
        print(f"  ↳ Using optimistic hard fallback (document assumed processable)")
        return {
            "validation": {
                "is_valid": True,
                "quality_score": 0.75,
                "issues": ["Validation response could not be parsed — assumed valid"],
            },
            "document_metadata": {
                "document_type": "unknown",
                "document_subtype": None,
                "document_date": None,
                "document_source": None,
                "provider": None,
            },
            "processability": {
                "can_extract_text": True,
                "estimated_confidence": 0.75,
                "language": "en",
            },
        }

    def _validation_hard_fallback(self, reason: str) -> Dict[str, Any]:
        """Return a hard-reject validation result with a specific reason."""
        return {
            "validation": {
                "is_valid": False,
                "quality_score": 0.0,
                "issues": [reason],
            },
            "document_metadata": {
                "document_type": "unknown",
                "document_subtype": None,
                "document_date": None,
                "document_source": None,
                "provider": None,
            },
            "processability": {
                "can_extract_text": False,
                "estimated_confidence": 0.0,
                "language": "en",
            },
        }

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Extract and parse the JSON answer from a raw MedGemma response.

        MedGemma 27B (Gemma 3 based) uses inference-time compute / thinking
        tokens. When thinking is not suppressed at the request level the model
        emits an extended reasoning block BEFORE the JSON answer:

            thought
            <multi-line reasoning — may include prompt-example JSON>
            ```json
            { "actual": "answer" }
            ```

        This means:
        - The FIRST JSON-like substring is usually mid-reasoning (copied from
          the prompt example), NOT the real answer.
        - The LAST complete JSON object in the text IS the real answer.

        Strategy waterfall (industry standard, used by LangChain, LlamaIndex):
          1. Strip the thought block entirely, then look for a JSON code block.
          2. Look for the last ```json … ``` code block in the full response.
          3. Attempt a direct json.loads on the post-thought remainder.
          4. Find the last outermost JSON object via right-to-left brace scan.
          5. json_repair — handles truncated / malformed JSON.
          6. Return a structured error dict so callers can gracefully degrade.
        """
        import json
        import re

        if not isinstance(response, str):
            if isinstance(response, dict):
                return response
            return {"error": f"Unexpected response type: {type(response)}"}

        original = response

        # ------------------------------------------------------------------ #
        # STRATEGY 1: Strip the complete thought block, extract last code fence
        # ------------------------------------------------------------------ #
        # MedGemma thinking block always starts with the literal word "thought"
        # (lower-case, at the very beginning of the output) followed by a
        # newline and multi-line reasoning. We identify the block boundary by
        # finding the last ```json … ``` section — that's the real answer.

        is_thinking_response = response.startswith("thought") or response.startswith(
            "```json"
        )  # sometimes code fence comes first

        if is_thinking_response:
            # Find the LAST ```json ... ``` block — that is always the answer,
            # not an example embedded in the reasoning.
            last_fence_start = response.rfind("```json")
            if last_fence_start == -1:
                last_fence_start = response.rfind("```")

            if last_fence_start != -1:
                fence_content = response[last_fence_start:]
                fence_match = re.search(
                    r"```(?:json)?\s*(\{.*?\})\s*```",
                    fence_content,
                    re.DOTALL,
                )
                if fence_match:
                    candidate = fence_match.group(1).strip()
                    candidate = self._clean_json_string(candidate)
                    try:
                        parsed = json.loads(candidate)
                        print(
                            f"  ✓ [S1] Extracted JSON from last code fence in thought response"
                        )
                        return parsed
                    except json.JSONDecodeError as e:
                        print(f"  ⚠️  [S1] Last code fence JSON invalid: {e}")

            # No code fence found — strip the thought prefix and continue with
            # the remaining strategies on the suffix.
            # Find where the reasoning ends: last blank line before a `{`
            after_thought = re.sub(r"^thought\s*\n", "", response, flags=re.IGNORECASE)
            response = after_thought.strip()

        # ------------------------------------------------------------------ #
        # STRATEGY 2: Last ```json … ``` block in ANY response
        # ------------------------------------------------------------------ #
        last_fence = response.rfind("```json")
        if last_fence == -1:
            last_fence = response.rfind("```")
        if last_fence != -1:
            fence_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```",
                response[last_fence:],
                re.DOTALL,
            )
            if fence_match:
                candidate = fence_match.group(1).strip()
                candidate = self._clean_json_string(candidate)
                try:
                    parsed = json.loads(candidate)
                    print(f"  ✓ [S2] Extracted JSON from code fence")
                    return parsed
                except json.JSONDecodeError as e:
                    print(f"  ⚠️  [S2] Code fence JSON invalid: {e}")

        # ------------------------------------------------------------------ #
        # STRATEGY 3: Direct parse of the (possibly stripped) response
        # ------------------------------------------------------------------ #
        cleaned = self._clean_json_string(response.strip())
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                print(f"  ✓ [S3] Direct JSON parse succeeded")
                return parsed
        except json.JSONDecodeError as e:
            print(f"  ⚠️  [S3] Direct parse failed: {e}")

        # ------------------------------------------------------------------ #
        # STRATEGY 4: Find the last outermost JSON object via right-to-left
        #             balanced brace scan.
        #
        # Why last and not first?  The thought block may contain prompt-example
        # JSON that looks structurally identical to the real answer. The real
        # answer is ALWAYS the final JSON object in the output.
        # ------------------------------------------------------------------ #
        json_str = self._extract_last_json_object(response)
        if json_str:
            json_str = self._clean_json_string(json_str)
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    print(
                        f"  ✓ [S4] Extracted last JSON object via brace scan ({len(json_str)} chars)"
                    )
                    return parsed
            except json.JSONDecodeError as e:
                print(f"  ⚠️  [S4] Brace-scan JSON invalid: {e}")

        # ------------------------------------------------------------------ #
        # STRATEGY 5: json_repair  — handles truncated / malformed JSON such
        # as missing closing braces, trailing commas, unquoted values, etc.
        # ------------------------------------------------------------------ #
        try:
            from json_repair import repair_json

            # Prefer the trimmed response; fall back to the full original.
            for label, candidate in [("trimmed", response), ("original", original)]:
                try:
                    repaired = repair_json(candidate, return_objects=True)
                    if isinstance(repaired, dict) and repaired:
                        print(
                            f"  ✓ [S5] json_repair recovered dict from {label} response"
                        )
                        return repaired
                except Exception:
                    pass
            print(f"  ⚠️  [S5] json_repair could not recover a dict")
        except ImportError:
            print(f"  ⚠️  [S5] json_repair not installed — run: pip install json-repair")
        except Exception as e:
            print(f"  ⚠️  [S5] json_repair error: {e}")

        # ------------------------------------------------------------------ #
        # STRATEGY 6: Structured error — lets callers apply graceful defaults
        # ------------------------------------------------------------------ #
        print(
            f"❌ [S6] All parsing strategies failed. Response sample: {original[:200]}"
        )
        return {
            "error": "Failed to parse JSON after all strategies",
            "raw_response": original[:500],
        }

    def _extract_last_json_object(self, text: str) -> Optional[str]:
        """
        Find the last complete top-level JSON object in `text` by scanning
        right-to-left from the last `}` and counting braces.

        Using the LAST object (not the first) is critical for thinking-model
        responses where earlier JSON-like content is part of the reasoning block.
        """
        last_close = text.rfind("}")
        if last_close == -1:
            return None

        depth = 0
        in_string = False
        escape_next = False

        for i in range(last_close, -1, -1):
            ch = text[i]

            if escape_next:
                escape_next = False
                continue

            # Walking backward: a backslash before the current char means the
            # NEXT char we visit (i-1) is escaped — but we can't know that
            # easily scanning backward. Instead we count leading backslashes.
            if ch == '"' and not in_string:
                # Count how many backslashes precede this quote
                n_bs = 0
                j = i - 1
                while j >= 0 and text[j] == "\\":
                    n_bs += 1
                    j -= 1
                if n_bs % 2 == 0:
                    in_string = True
                continue

            if ch == '"' and in_string:
                n_bs = 0
                j = i - 1
                while j >= 0 and text[j] == "\\":
                    n_bs += 1
                    j -= 1
                if n_bs % 2 == 0:
                    in_string = False
                continue

            if in_string:
                continue

            if ch == "}":
                depth += 1
            elif ch == "{":
                depth -= 1
                if depth == 0:
                    return text[i : last_close + 1]

        return None

    def _clean_json_string(self, json_str: str) -> str:
        """
        Normalise common LLM JSON quirks before parsing.
        Mirrors the approach used by LangChain, AutoGPT, and LlamaIndex.
        """
        import re

        # 1. Remove markdown code-fence markers if still present
        json_str = re.sub(r"^```(?:json)?\s*", "", json_str.strip())
        json_str = re.sub(r"\s*```$", "", json_str.strip())

        # 2. Unescape single quotes (invalid JSON escape)
        json_str = json_str.replace("\\'", "'")

        # 3. Remove trailing commas before } or ]
        json_str = re.sub(r",\s*([}\]])", r"\1", json_str)

        # 4. Strip single-line and multi-line comments
        json_str = re.sub(r"//[^\n]*", "", json_str)
        json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)

        # 5. Replace Python-style None/True/False with JSON equivalents
        json_str = re.sub(r"\bNone\b", "null", json_str)
        json_str = re.sub(r"\bTrue\b", "true", json_str)
        json_str = re.sub(r"\bFalse\b", "false", json_str)

        return json_str

    async def process_document(
        self,
        image_bytes: bytes,
        filename: str,
        file_type: str,
        db_session: Optional[Session] = None,
        user_id: Optional[str] = None,
        document_id: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process document through 4-agent pipeline.

        Args:
            image_bytes: Raw image bytes from upload
            filename: Original filename
            file_type: Type of file (PDF or Image)
            db_session: Database session for relationship mapping
            user_id: User ID for relationship mapping
            document_id: Document ID being processed
            job_id: Unique job ID for progress tracking (auto-generated if not provided)

        Returns:
            Combined results from all 4 agents (including job_id for progress tracking)
        """
        # Create or use provided job_id for progress tracking
        if not job_id:
            job_id = self.create_job_id(filename)

        print(f"\n{'='*60}")
        print(f"🤖 4-AGENT PIPELINE STARTED")
        print(f"{'='*60}")
        print(f"Job ID: {job_id}")
        print(f"Document: {filename}")
        print(f"User: {user_id}")
        print(f"File Type: {file_type}")
        print(f"Image Size: {len(image_bytes)} bytes\n")

        # Initialize progress tracking
        self.update_progress(
            job_id, "validating", "in_progress", "Starting document validation..."
        )

        # Initialize state with all required fields
        initial_state: AgentState = {
            "image_bytes": image_bytes,
            "filename": filename,
            "file_type": file_type,
            "job_id": job_id,
            "db_session": db_session,
            "user_id": user_id,
            "document_id": document_id,
            "validation": {},
            "clinical_data": {},
            "summaries": {},
            "relationships": {},
            "is_valid": False,
            "should_continue": False,
            "needs_review": False,
            "errors": [],
        }

        # Run the agent graph
        try:
            print("Stage 1: Document Validation...")
            final_state = await self.graph.ainvoke(initial_state)

            # Check if validation passed
            if not final_state.get("is_valid", False):
                validation = final_state.get("validation", {})
                issues = validation.get("validation", {}).get(
                    "issues", ["Unknown validation error"]
                )
                print(f"\n{'='*60}")
                print(f"❌ DOCUMENT VALIDATION FAILED")
                print(f"{'='*60}")
                print(f"Issues: {', '.join(issues)}\n")

                # Update progress to failed
                self.update_progress(
                    job_id,
                    "validating",
                    "failed",
                    "Document validation failed",
                    error=", ".join(issues),
                )

                return {
                    "success": False,
                    "job_id": job_id,
                    "validation_failed": True,
                    "validation": final_state.get("validation", {}),
                    "clinical_data": {},
                    "summaries": {},
                    "relationships": {},
                    "needs_review": False,
                    "errors": final_state.get("errors", []),
                }

            print(f"\n{'='*60}")
            print(f"✅ ALL 4 AGENTS COMPLETED SUCCESSFULLY")
            print(f"{'='*60}\n")

            # Mark as completed
            self.update_progress(
                job_id, "completed", "completed", "All agents completed successfully"
            )

            # No verification agent, so never flag for review
            results = {
                "success": True,
                "job_id": job_id,
                "validation": final_state.get("validation", {}),
                "clinical_data": final_state.get("clinical_data", {}),
                "summaries": final_state.get("summaries", {}),
                "relationships": final_state.get("relationships", {}),
                "needs_review": False,
                "errors": final_state.get("errors", []),
            }

            # Serialize datetime objects to ISO strings for JSON storage
            return json.loads(json.dumps(results, default=json_serializer))
        except Exception as e:
            print(f"❌ Agent orchestration failed: {e}")
            import traceback

            traceback.print_exc()

            # Update progress to failed
            self.update_progress(
                job_id, "validating", "failed", "Pipeline error", error=str(e)
            )

            return {
                "success": False,
                "job_id": job_id,
                "error": str(e),
                "validation": {},
                "clinical_data": {},
                "summaries": {},
                "relationships": {},
                "needs_review": False,
            }
