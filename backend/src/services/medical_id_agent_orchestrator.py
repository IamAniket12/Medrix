"""
Medical ID Agent Orchestrator using LangGraph.
Two specialized agents for Medical ID data retrieval:
- Agent 1: Permanent ID Data Agent (critical emergency info)
- Agent 2: Temporary Summary Agent (comprehensive medical history)
"""

import asyncio
from typing import Dict, Any, List, TypedDict, Annotated, Optional
from typing_extensions import TypedDict as ExtTypedDict
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field, field_validator
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import operator
from sqlalchemy.orm import Session
from datetime import datetime, date
import json
from decimal import Decimal

from ..models import (
    User,
    ClinicalCondition,
    ClinicalMedication,
    ClinicalAllergy,
    ClinicalLabResult,
    ClinicalVitalSign,
    ClinicalProcedure,
    ClinicalImmunization,
)


def json_serializer(obj):
    """Helper to serialize datetime, date, and Decimal objects for JSON."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


# ============================================================
# PYDANTIC SCHEMAS FOR AGENT RESPONSES
# ============================================================


class EmergencyContact(BaseModel):
    """Emergency contact information."""

    name: Optional[str] = None
    phone: Optional[str] = None
    relationship: Optional[str] = None


class CriticalConditionInfo(BaseModel):
    """Critical condition for permanent ID."""

    name: str
    severity: Optional[str] = None
    status: str = "active"
    diagnosed_date: Optional[str] = None
    priority_score: float = Field(ge=0, le=1, description="0-1 priority for display")


class CriticalAllergyInfo(BaseModel):
    """Life-threatening allergy for permanent ID."""

    allergen: str
    reaction: Optional[str] = None
    severity: str  # Should be severe or life-threatening
    priority_score: float = Field(ge=0, le=1, description="0-1 priority for display")


class PermanentIDData(BaseModel):
    """Structured data for permanent medical ID card."""

    patient_name: str
    date_of_birth: Optional[str] = None
    blood_type: Optional[str] = None
    gender: Optional[str] = None

    # Critical medical info (ALL conditions and allergies, no limit)
    chronic_conditions: List[CriticalConditionInfo] = Field(default_factory=list)
    life_threatening_allergies: List[CriticalAllergyInfo] = Field(default_factory=list)

    # Emergency contact
    emergency_contact: Optional[EmergencyContact] = None

    # Metadata
    card_purpose: str = "Emergency medical identification"
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ComprehensiveMedication(BaseModel):
    """Medication for temporary summary."""

    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    indication: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    prescriber: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None


class ComprehensiveCondition(BaseModel):
    """Condition for temporary summary."""

    name: str
    status: Optional[str] = None
    diagnosed_date: Optional[str] = None
    severity: Optional[str] = None
    icd10_code: Optional[str] = None
    body_site: Optional[str] = None
    notes: Optional[str] = None


class VitalSign(BaseModel):
    """Vital sign reading."""

    measurement_date: Optional[str] = None
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    heart_rate: Optional[float] = None
    respiratory_rate: Optional[float] = None
    temperature: Optional[float] = None
    temperature_unit: Optional[str] = None
    oxygen_saturation: Optional[float] = None
    weight: Optional[float] = None
    weight_unit: Optional[str] = None
    height: Optional[float] = None
    height_unit: Optional[str] = None
    bmi: Optional[float] = None
    notes: Optional[str] = None


# Keep old name as alias for backward compat
RecentVitalSign = VitalSign


class LabResult(BaseModel):
    """Lab result (normal or abnormal)."""

    test_name: str
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    test_date: Optional[str] = None
    is_abnormal: Optional[bool] = None
    abnormal_flag: Optional[str] = None
    ordering_provider: Optional[str] = None
    lab_facility: Optional[str] = None
    notes: Optional[str] = None


# Keep old name as alias for backward compat
AbnormalLabResult = LabResult


class ClinicalAISummary(BaseModel):
    """
    AI-generated clinical summary from MedGemma.
    Structured for quick doctor review — no need to read full history.
    """

    clinical_overview: str = ""
    """2-3 sentence narrative: who is this patient, what are the main active issues."""

    active_concerns: List[str] = Field(default_factory=list)
    """Top active medical concerns ranked by clinical priority."""

    medication_review: str = ""
    """Key notes: interactions, duplicates, high-risk meds, compliance flags."""

    lab_flags: str = ""
    """Abnormal lab findings that need attention."""

    vital_trend: str = ""
    """Notable vital sign patterns or alerts."""

    risk_level: str = "unknown"
    """Overall risk: low / moderate / high / critical."""

    recommended_actions: List[str] = Field(default_factory=list)
    """Suggested follow-ups or actions for the receiving clinician."""

    ai_confidence: str = "moderate"
    """Model confidence: low / moderate / high."""

    @field_validator(
        "clinical_overview",
        "medication_review",
        "lab_flags",
        "vital_trend",
        "risk_level",
        "ai_confidence",
        mode="before",
    )
    @classmethod
    def coerce_list_to_str(cls, v: Any) -> str:
        """MedGemma sometimes returns string fields as lists — join them."""
        if isinstance(v, list):
            return "; ".join(str(item) for item in v)
        return v if v is not None else ""

    @field_validator("active_concerns", "recommended_actions", mode="before")
    @classmethod
    def coerce_str_to_list(cls, v: Any) -> List[str]:
        """Ensure list fields are always lists even if model returns a string."""
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v if v is not None else []


class TemporarySummaryData(BaseModel):
    """Comprehensive medical data for temporary summary."""

    patient_name: str
    date_of_birth: Optional[str] = None
    blood_type: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None

    # Comprehensive medical data — ALL records, no filters
    all_medications: List[ComprehensiveMedication] = Field(default_factory=list)
    all_conditions: List[ComprehensiveCondition] = Field(default_factory=list)
    all_allergies: List[Dict[str, Any]] = Field(default_factory=list)
    all_vitals: List[VitalSign] = Field(default_factory=list)
    all_lab_results: List[LabResult] = Field(default_factory=list)
    all_procedures: List[Dict[str, Any]] = Field(default_factory=list)
    immunizations: List[Dict[str, Any]] = Field(default_factory=list)

    # Provider and emergency info
    primary_care_physician: Optional[str] = None
    emergency_contact: Optional[EmergencyContact] = None

    # AI-generated clinical summary (from MedGemma)
    clinical_ai_summary: Optional[ClinicalAISummary] = None

    # Summary metadata
    summary_purpose: str = "Temporary medical history for healthcare provider access"
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    valid_until: Optional[str] = None


# ============================================================
# AGENT STATE
# ============================================================


class MedicalIDAgentState(ExtTypedDict):
    """State shared between Medical ID agents."""

    # Input context
    db_session: Session
    user_id: str
    operation_type: str  # "permanent_id" or "temporary_summary"

    # Agent outputs
    permanent_id_data: Optional[Dict[str, Any]]  # Agent 1 output
    temporary_summary_data: Optional[Dict[str, Any]]  # Agent 2 output
    clinical_ai_summary: Optional[Dict[str, Any]]  # Agent 3 output

    # Processing metadata
    errors: Annotated[List[str], operator.add]


class MedicalIDAgentOrchestrator:
    """Orchestrates agents for Medical ID data retrieval and intelligent filtering."""

    def __init__(self, settings):
        """
        Initialize the Medical ID agent orchestrator.

        Args:
            settings: Application settings (for LLM configuration)
        """
        self.settings = settings

        # HTTP / Colab mode or Vertex AI mode (same as main orchestrator)
        http_url = getattr(settings, "medgemma_endpoint_url", None)
        if http_url:
            self._mode = "http"
            self._http_url = http_url.rstrip("/")
            self.endpoint = None
            print(f"✓ MedicalIDAgentOrchestrator → HTTP / Colab mode: {self._http_url}")
        else:
            self._mode = "vertex"
            self._http_url = None
            from google.cloud import aiplatform

            self.endpoint = aiplatform.Endpoint(
                endpoint_name=f"projects/{settings.google_cloud_project}/locations/{settings.vertex_ai_location}/endpoints/{settings.medgemma_endpoint_id}"
            )

        # Build agent graphs
        self.permanent_id_graph = self._build_permanent_id_graph()
        self.temporary_summary_graph = self._build_temporary_summary_graph()

    def _build_permanent_id_graph(self) -> StateGraph:
        """
        Build the Permanent ID Agent workflow.
        Single agent that retrieves and prioritizes critical emergency data.
        """
        workflow = StateGraph(MedicalIDAgentState)
        workflow.add_node("permanent_id_agent", self._permanent_id_agent)
        workflow.set_entry_point("permanent_id_agent")
        workflow.add_edge("permanent_id_agent", END)
        return workflow.compile()

    def _build_temporary_summary_graph(self) -> StateGraph:
        """
        Build the Temporary Summary Agent workflow.
        Agent 1: DB fetcher — retrieves all patient records.
        Agent 2: MedGemma clinical summarizer — generates doctor-facing AI summary.
        """
        workflow = StateGraph(MedicalIDAgentState)
        workflow.add_node("temporary_summary_agent", self._temporary_summary_agent)
        workflow.add_node("clinical_summarizer", self._clinical_summarizer_agent)
        workflow.set_entry_point("temporary_summary_agent")
        workflow.add_edge("temporary_summary_agent", "clinical_summarizer")
        workflow.add_edge("clinical_summarizer", END)
        return workflow.compile()

    async def generate_permanent_id_data(
        self, db: Session, user_id: str
    ) -> PermanentIDData:
        """
        Run the Permanent ID Agent to retrieve critical emergency data.

        Args:
            db: Database session
            user_id: User ID to generate data for

        Returns:
            PermanentIDData: Structured permanent ID data
        """
        print(f"🔍 Medical ID Agent: Generating Permanent ID Data for user {user_id}")

        initial_state = {
            "db_session": db,
            "user_id": user_id,
            "operation_type": "permanent_id",
            "permanent_id_data": None,
            "temporary_summary_data": None,
            "errors": [],
        }

        result = await self.permanent_id_graph.ainvoke(initial_state)

        if result["errors"]:
            print(f"⚠️  Permanent ID Agent completed with errors: {result['errors']}")

        return PermanentIDData(**result["permanent_id_data"])

    async def generate_temporary_summary_data(
        self, db: Session, user_id: str, expires_at: datetime
    ) -> TemporarySummaryData:
        """
        Run the Temporary Summary Agent to retrieve comprehensive medical history.

        Args:
            db: Database session
            user_id: User ID to generate data for
            expires_at: When the summary expires

        Returns:
            TemporarySummaryData: Structured comprehensive medical data
        """
        print(
            f"🔍 Medical ID Agent: Generating Temporary Summary Data for user {user_id}"
        )

        initial_state = {
            "db_session": db,
            "user_id": user_id,
            "operation_type": "temporary_summary",
            "permanent_id_data": None,
            "temporary_summary_data": None,
            "clinical_ai_summary": None,
            "errors": [],
        }

        result = await self.temporary_summary_graph.ainvoke(initial_state)

        if result["errors"]:
            print(
                f"⚠️  Temporary Summary Agent completed with errors: {result['errors']}"
            )

        raw = result["temporary_summary_data"]
        print(f"📦 Raw summary keys: {list(raw.keys())}")
        print(f"  all_medications: {len(raw.get('all_medications', []))}")
        print(f"  all_vitals: {len(raw.get('all_vitals', []))}")
        print(f"  all_lab_results: {len(raw.get('all_lab_results', []))}")
        if raw.get("all_vitals"):
            print(f"  first vital sample: {raw['all_vitals'][0]}")
        print(f"  emergency_contact: {raw.get('emergency_contact')}")

        try:
            summary_data = TemporarySummaryData(**raw)
        except Exception as e:
            print(f"❌ TemporarySummaryData validation error: {e}")
            import traceback

            traceback.print_exc()
            raise

        summary_data.valid_until = expires_at.isoformat()

        # Attach AI clinical summary if available
        if result.get("clinical_ai_summary"):
            try:
                summary_data.clinical_ai_summary = ClinicalAISummary(
                    **result["clinical_ai_summary"]
                )
                print(
                    f"✓ Clinical AI summary attached (risk: {summary_data.clinical_ai_summary.risk_level})"
                )
            except Exception as e:
                print(f"⚠️  Could not attach AI summary: {e}")

        return summary_data

    async def _permanent_id_agent(self, state: MedicalIDAgentState) -> Dict[str, Any]:
        """
        Agent 1: Permanent ID Data Agent
        Retrieves and intelligently prioritizes critical medical data for emergency ID card.

        Focus:
        - Top 3 chronic conditions (diabetes, hypertension, heart disease, epilepsy, etc.)
        - Top 3 life-threatening allergies (severity: severe or life-threatening)
        - Patient demographics and emergency contact
        """
        try:
            db = state["db_session"]
            user_id = state["user_id"]

            # Query user demographics
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")

            # Query ALL chronic conditions (active only)
            all_conditions = (
                db.query(ClinicalCondition)
                .filter(
                    ClinicalCondition.user_id == user_id,
                    ClinicalCondition.deleted_at.is_(None),
                )
                .all()
            )

            # Query ALL allergies (severe and life-threatening)
            critical_allergies = (
                db.query(ClinicalAllergy)
                .filter(
                    ClinicalAllergy.user_id == user_id,
                    ClinicalAllergy.deleted_at.is_(None),
                    ClinicalAllergy.is_active == True,
                    ClinicalAllergy.severity.in_(["severe", "life-threatening"]),
                )
                .all()
            )

            # Build PermanentIDData with ALL conditions and allergies (no limiting)
            permanent_data = {
                "patient_name": user.name or "Unknown Patient",
                "date_of_birth": (
                    user.date_of_birth.isoformat() if user.date_of_birth else None
                ),
                "blood_type": user.blood_type,
                "gender": user.gender,
                "chronic_conditions": [
                    {
                        "name": c.name,
                        "severity": c.severity,
                        "status": c.status or "active",
                        "diagnosed_date": (
                            c.diagnosed_date.isoformat() if c.diagnosed_date else None
                        ),
                        "priority_score": 1.0,  # All conditions are important
                    }
                    for c in all_conditions
                ],
                "life_threatening_allergies": [
                    {
                        "allergen": a.allergen,
                        "reaction": a.reaction,
                        "severity": a.severity,
                        "priority_score": 1.0,  # All allergies are critical
                    }
                    for a in critical_allergies
                ],
                "emergency_contact": (
                    {
                        "name": user.emergency_contact_name,
                        "phone": user.emergency_contact_phone,
                    }
                    if user.emergency_contact_name
                    else None
                ),
            }

            print(f"✓ Permanent ID Agent: Retrieved data for {user.name}")
            print(f"  Conditions: {len(permanent_data['chronic_conditions'])}")
            print(f"  Allergies: {len(permanent_data['life_threatening_allergies'])}")

            return {"permanent_id_data": permanent_data}

        except Exception as e:
            print(f"❌ Permanent ID Agent error: {e}")
            return {
                "permanent_id_data": {
                    "patient_name": "Error",
                    "chronic_conditions": [],
                    "life_threatening_allergies": [],
                },
                "errors": [f"Permanent ID Agent: {str(e)}"],
            }

    async def _temporary_summary_agent(
        self, state: MedicalIDAgentState
    ) -> Dict[str, Any]:
        """
        Agent 2: Temporary Summary Agent
        Retrieves comprehensive medical history for temporary healthcare provider access.

        Includes:
        - ALL active medications
        - ALL conditions
        - ALL allergies
        - Recent vital signs (last 3)
        - Abnormal lab results (last 6 months)
        - Recent procedures (last 12 months)
        - Current immunizations
        """
        try:
            db = state["db_session"]
            user_id = state["user_id"]

            # Query user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")

            # Query ALL medications (active and historical)
            medications = (
                db.query(ClinicalMedication)
                .filter(
                    ClinicalMedication.user_id == user_id,
                    ClinicalMedication.deleted_at.is_(None),
                )
                .order_by(
                    ClinicalMedication.is_active.desc(),
                    ClinicalMedication.start_date.desc(),
                )
                .all()
            )

            # Query all conditions
            conditions = (
                db.query(ClinicalCondition)
                .filter(
                    ClinicalCondition.user_id == user_id,
                    ClinicalCondition.deleted_at.is_(None),
                )
                .all()
            )

            # Query ALL allergies (active and historical)
            allergies = (
                db.query(ClinicalAllergy)
                .filter(
                    ClinicalAllergy.user_id == user_id,
                    ClinicalAllergy.deleted_at.is_(None),
                )
                .order_by(ClinicalAllergy.is_active.desc())
                .all()
            )

            # Query ALL vitals (no limit)
            vitals = (
                db.query(ClinicalVitalSign)
                .filter(
                    ClinicalVitalSign.user_id == user_id,
                    ClinicalVitalSign.deleted_at.is_(None),
                )
                .order_by(ClinicalVitalSign.measurement_date.desc())
                .all()
            )

            # Query ALL lab results (normal and abnormal)
            all_labs = (
                db.query(ClinicalLabResult)
                .filter(
                    ClinicalLabResult.user_id == user_id,
                    ClinicalLabResult.deleted_at.is_(None),
                )
                .order_by(ClinicalLabResult.test_date.desc())
                .all()
            )

            # Query ALL procedures
            procedures = (
                db.query(ClinicalProcedure)
                .filter(
                    ClinicalProcedure.user_id == user_id,
                    ClinicalProcedure.deleted_at.is_(None),
                )
                .order_by(ClinicalProcedure.performed_date.desc())
                .all()
            )

            # Query ALL immunizations
            immunizations = (
                db.query(ClinicalImmunization)
                .filter(
                    ClinicalImmunization.user_id == user_id,
                    ClinicalImmunization.deleted_at.is_(None),
                )
                .order_by(ClinicalImmunization.administration_date.desc())
                .all()
            )

            # Build comprehensive summary data — ALL records, no filters
            summary_data = {
                "patient_name": user.name or "Unknown Patient",
                "date_of_birth": (
                    user.date_of_birth.isoformat() if user.date_of_birth else None
                ),
                "blood_type": user.blood_type,
                "gender": user.gender,
                "phone": user.phone,
                "all_medications": [
                    {
                        "name": m.name,
                        "dosage": m.dosage,
                        "frequency": m.frequency,
                        "route": m.route,
                        "indication": m.indication,
                        "start_date": (
                            m.start_date.isoformat() if m.start_date else None
                        ),
                        "end_date": (m.end_date.isoformat() if m.end_date else None),
                        "prescriber": m.prescriber,
                        "is_active": m.is_active,
                        "notes": m.notes,
                    }
                    for m in medications
                ],
                "all_conditions": [
                    {
                        "name": c.name,
                        "status": c.status,
                        "diagnosed_date": (
                            c.diagnosed_date.isoformat() if c.diagnosed_date else None
                        ),
                        "severity": c.severity,
                        "icd10_code": c.icd10_code,
                        "body_site": c.body_site,
                        "notes": c.notes,
                    }
                    for c in conditions
                ],
                "all_allergies": [
                    {
                        "allergen": a.allergen,
                        "reaction": a.reaction,
                        "severity": a.severity,
                        "allergy_type": a.allergy_type,
                        "is_active": a.is_active,
                        "verified_date": (
                            a.verified_date.isoformat() if a.verified_date else None
                        ),
                        "notes": a.notes,
                    }
                    for a in allergies
                ],
                "all_vitals": [
                    {
                        "measurement_date": (
                            v.measurement_date.isoformat()
                            if v.measurement_date
                            else None
                        ),
                        "systolic_bp": v.systolic_bp,
                        "diastolic_bp": v.diastolic_bp,
                        "heart_rate": v.heart_rate,
                        "respiratory_rate": v.respiratory_rate,
                        "temperature": float(v.temperature) if v.temperature else None,
                        "temperature_unit": v.temperature_unit,
                        "oxygen_saturation": v.oxygen_saturation,
                        "weight": float(v.weight) if v.weight else None,
                        "weight_unit": v.weight_unit,
                        "height": float(v.height) if v.height else None,
                        "height_unit": v.height_unit,
                        "bmi": float(v.bmi) if v.bmi else None,
                        "notes": v.notes,
                    }
                    for v in vitals
                ],
                "all_lab_results": [
                    {
                        "test_name": lab.test_name,
                        "value": lab.value,
                        "unit": lab.unit,
                        "reference_range": lab.reference_range,
                        "test_date": (
                            lab.test_date.isoformat() if lab.test_date else None
                        ),
                        "is_abnormal": lab.is_abnormal,
                        "abnormal_flag": lab.abnormal_flag,
                        "ordering_provider": lab.ordering_provider,
                        "lab_facility": lab.lab_facility,
                        "notes": lab.notes,
                    }
                    for lab in all_labs
                ],
                "all_procedures": [
                    {
                        "procedure_name": p.procedure_name,
                        "performed_date": (
                            p.performed_date.isoformat() if p.performed_date else None
                        ),
                        "provider": p.provider,
                        "facility": p.facility,
                        "indication": p.indication,
                        "outcome": p.outcome,
                        "body_site": p.body_site,
                    }
                    for p in procedures
                ],
                "immunizations": [
                    {
                        "vaccine_name": imm.vaccine_name,
                        "administration_date": (
                            imm.administration_date.isoformat()
                            if imm.administration_date
                            else None
                        ),
                        "dose_number": imm.dose_number,
                        "manufacturer": imm.manufacturer,
                        "facility": imm.facility,
                        "administered_by": imm.administered_by,
                    }
                    for imm in immunizations
                ],
                "primary_care_physician": user.primary_care_physician,
                "emergency_contact": (
                    {
                        "name": user.emergency_contact_name,
                        "phone": user.emergency_contact_phone,
                    }
                    if user.emergency_contact_name
                    else None
                ),
            }

            print(f"✓ Temporary Summary Agent: Retrieved ALL data for {user.name}")
            print(f"  Medications (all): {len(summary_data['all_medications'])}")
            print(f"  Conditions: {len(summary_data['all_conditions'])}")
            print(f"  Allergies (all): {len(summary_data['all_allergies'])}")
            print(f"  Vitals (all): {len(summary_data['all_vitals'])}")
            print(f"  Lab Results (all): {len(summary_data['all_lab_results'])}")
            print(f"  Procedures: {len(summary_data['all_procedures'])}")
            print(f"  Immunizations: {len(summary_data['immunizations'])}")

            return {"temporary_summary_data": summary_data}

        except Exception as e:
            print(f"❌ Temporary Summary Agent error: {e}")
            return {
                "temporary_summary_data": {
                    "patient_name": "Error",
                    "all_medications": [],
                    "all_conditions": [],
                    "all_allergies": [],
                    "all_vitals": [],
                    "all_lab_results": [],
                    "all_procedures": [],
                    "immunizations": [],
                },
                "errors": [f"Temporary Summary Agent: {str(e)}"],
            }

    async def _clinical_summarizer_agent(
        self, state: MedicalIDAgentState
    ) -> Dict[str, Any]:
        """
        Agent 3: Clinical Summarizer (MedGemma)
        Reads all fetched patient data and generates a structured AI clinical
        summary optimised for a receiving doctor — risk level, active concerns,
        medication review, lab flags, and recommended actions.
        """
        try:
            raw = state.get("temporary_summary_data", {})
            if not raw or raw.get("patient_name") == "Error":
                print("⚠️  Skipping clinical summarizer — no valid patient data")
                return {"clinical_ai_summary": None}

            # ── Build a compact, information-dense text representation ──────
            lines = []
            lines.append(f"PATIENT: {raw.get('patient_name', 'Unknown')}")
            if raw.get("date_of_birth"):
                lines.append(f"DOB: {raw['date_of_birth']}")
            if raw.get("blood_type"):
                lines.append(f"Blood Type: {raw['blood_type']}")
            if raw.get("gender"):
                lines.append(f"Gender: {raw['gender']}")

            meds = raw.get("all_medications", [])
            if meds:
                lines.append(f"\nMEDICATIONS ({len(meds)} total):")
                for m in meds:
                    status = "ACTIVE" if m.get("is_active") else "HISTORICAL"
                    entry = f"  [{status}] {m.get('name', 'Unknown')}"
                    if m.get("dosage"):
                        entry += f" {m['dosage']}"
                    if m.get("frequency"):
                        entry += f", {m['frequency']}"
                    if m.get("indication"):
                        entry += f" (for: {m['indication']})"
                    lines.append(entry)

            conditions = raw.get("all_conditions", [])
            if conditions:
                lines.append(f"\nCONDITIONS ({len(conditions)} total):")
                for c in conditions:
                    entry = f"  {c.get('name', 'Unknown')}"
                    if c.get("status"):
                        entry += f" [{c['status']}]"
                    if c.get("severity"):
                        entry += f" - {c['severity']}"
                    if c.get("icd10_code"):
                        entry += f" (ICD10: {c['icd10_code']})"
                    lines.append(entry)

            allergies = raw.get("all_allergies", [])
            if allergies:
                lines.append(f"\nALLERGIES ({len(allergies)} total):")
                for a in allergies:
                    entry = f"  {a.get('allergen', 'Unknown')}"
                    if a.get("severity"):
                        entry += f" - {a['severity'].upper()}"
                    if a.get("reaction"):
                        entry += f" (reaction: {a['reaction']})"
                    lines.append(entry)

            vitals = raw.get("all_vitals", [])
            if vitals:
                lines.append(f"\nVITAL SIGNS (most recent {min(len(vitals), 3)}):")
                for v in vitals[:3]:
                    parts = []
                    if v.get("systolic_bp") and v.get("diastolic_bp"):
                        parts.append(f"BP {v['systolic_bp']}/{v['diastolic_bp']}")
                    if v.get("heart_rate"):
                        parts.append(f"HR {v['heart_rate']}")
                    if v.get("temperature"):
                        parts.append(f"Temp {v['temperature']}")
                    if v.get("oxygen_saturation"):
                        parts.append(f"SpO2 {v['oxygen_saturation']}%")
                    if v.get("bmi"):
                        parts.append(f"BMI {v['bmi']}")
                    date = str(v.get("measurement_date", ""))[:10] or "unknown date"
                    lines.append(
                        f"  [{date}] {', '.join(parts) if parts else 'no values'}"
                    )

            labs = raw.get("all_lab_results", [])
            abnormal_labs = [l for l in labs if l.get("is_abnormal")]
            if labs:
                lines.append(
                    f"\nLAB RESULTS ({len(labs)} total, {len(abnormal_labs)} abnormal):"
                )
                for l in labs[:10]:  # cap at 10 for prompt length
                    flag = " [ABNORMAL]" if l.get("is_abnormal") else ""
                    entry = f"  {l.get('test_name', 'Unknown')}{flag}"
                    if l.get("value"):
                        entry += f": {l['value']}"
                    if l.get("unit"):
                        entry += f" {l['unit']}"
                    if l.get("reference_range"):
                        entry += f" (ref: {l['reference_range']})"
                    if l.get("test_date"):
                        entry += f" on {str(l['test_date'])[:10]}"
                    lines.append(entry)

            procedures = raw.get("all_procedures", [])
            if procedures:
                lines.append(f"\nPROCEDURES ({len(procedures)} total):")
                for p in procedures[:5]:
                    entry = f"  {p.get('procedure_name', 'Unknown')}"
                    if p.get("performed_date"):
                        entry += f" on {str(p['performed_date'])[:10]}"
                    if p.get("outcome"):
                        entry += f" ({p['outcome']})"
                    lines.append(entry)

            patient_context = "\n".join(lines)

            # ── Carefully crafted clinical summarization prompt ────────────
            prompt = f"""You are a clinical decision support AI. A patient's complete medical record has been extracted from their documents. Your task is to produce a structured clinical briefing for a receiving doctor or specialist who needs to quickly understand this patient.

PATIENT MEDICAL RECORD:
{patient_context}

Generate a JSON object with exactly this structure. Be concise, clinically precise, and flag anything that requires immediate attention:

{{
  "clinical_overview": "<2-3 sentence narrative: who is this patient, primary diagnoses, overall health status>",
  "active_concerns": ["<concern 1>", "<concern 2>", ...],
  "medication_review": "<key notes: high-risk medications, potential interactions, duplicate therapies, or 'No concerns identified'>",
  "lab_flags": "<critical or abnormal lab findings that require follow-up, or 'No abnormal results'>",
  "vital_trend": "<notable vital sign patterns or 'Vitals within normal limits' or 'No vital sign data'>",
  "risk_level": "<one of: low | moderate | high | critical>",
  "recommended_actions": ["<action 1>", "<action 2>", ...],
  "ai_confidence": "<one of: low | moderate | high>"
}}

RULES:
- active_concerns: list the top 3-5 issues that need clinical attention, ordered by priority
- risk_level: base on severity of conditions, abnormal labs, medication risks
- recommended_actions: practical next steps (monitoring, referrals, tests, medication reviews)
- If data is missing or sparse, note it in clinical_overview and set ai_confidence to "low"
- Output ONLY the JSON object, no markdown, no explanation"""

            print(f"🧠 Clinical Summarizer: Calling MedGemma...")
            llm_response = await self._call_llm_text_only(prompt, output_format="json")
            print(f"✓ MedGemma responded ({len(llm_response)} chars)")

            # ── Parse and validate with Pydantic ─────────────────────────
            parsed = self._parse_json_response(llm_response)

            if not parsed:
                print("⚠️  MedGemma returned empty or unparseable JSON")
                return {
                    "clinical_ai_summary": {
                        "clinical_overview": "AI summary unavailable — model returned no parseable output.",
                        "active_concerns": [],
                        "medication_review": "",
                        "lab_flags": "",
                        "vital_trend": "",
                        "risk_level": "unknown",
                        "recommended_actions": [],
                        "ai_confidence": "low",
                    }
                }

            # Validate through Pydantic
            validated = ClinicalAISummary(
                **{
                    "clinical_overview": parsed.get("clinical_overview", ""),
                    "active_concerns": parsed.get("active_concerns", []),
                    "medication_review": parsed.get("medication_review", ""),
                    "lab_flags": parsed.get("lab_flags", ""),
                    "vital_trend": parsed.get("vital_trend", ""),
                    "risk_level": parsed.get("risk_level", "unknown"),
                    "recommended_actions": parsed.get("recommended_actions", []),
                    "ai_confidence": parsed.get("ai_confidence", "moderate"),
                }
            )

            print(
                f"✓ Clinical summary validated — Risk: {validated.risk_level} | Confidence: {validated.ai_confidence}"
            )
            return {"clinical_ai_summary": validated.model_dump()}

        except Exception as e:
            print(f"❌ Clinical Summarizer error: {e}")
            import traceback

            traceback.print_exc()
            # Non-fatal — return empty summary so PDF still generates
            return {
                "clinical_ai_summary": {
                    "clinical_overview": f"AI summary generation failed: {str(e)}",
                    "active_concerns": [],
                    "medication_review": "",
                    "lab_flags": "",
                    "vital_trend": "",
                    "risk_level": "unknown",
                    "recommended_actions": [],
                    "ai_confidence": "low",
                },
                "errors": [f"Clinical Summarizer: {str(e)}"],
            }

    # ============================================================
    # LLM CALL METHODS
    # ============================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    async def _call_llm_text_only(
        self, prompt: str, output_format: str = "json"
    ) -> str:
        """
        Call LLM with text-only prompt (no image).

        Args:
            prompt: The user prompt
            output_format: Either "json" for structured data or "text" for plain text

        Returns:
            str: The LLM response

        Uses the same chatCompletions instances format as the main orchestrator.
        """
        import re

        # Different system prompts based on output format
        if output_format == "json":
            system_content = (
                "You are a medical AI assistant. "
                "Your ONLY output must be a single, valid JSON object. "
                "Do NOT include any explanations, reasoning, markdown "
                "formatting, code fences, or additional text. "
                "Output the JSON object and nothing else."
            )
        else:  # plain text
            system_content = (
                "You are a medical AI assistant. "
                "Provide clear, concise medical guidance. "
                "Output ONLY plain text without any markdown formatting, "
                "bold/italic markers, code blocks, or special characters. "
                "Write naturally as if speaking to a healthcare provider."
            )

        instances = [
            {
                "@requestFormat": "chatCompletions",
                "messages": [
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "text",
                                "text": system_content,
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    },
                ],
                "thinking": {"type": "disabled"},
                "max_tokens": 8192,
                "temperature": 0.0,
            }
        ]

        if self._mode == "http":
            # HTTP/Colab mode — same format as agent_orchestrator.py
            import httpx

            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    print(
                        f"  → [MedicalID] Sending text-only request to {self._http_url}/predict"
                    )
                    resp = await client.post(
                        f"{self._http_url}/predict",
                        json={"instances": instances},
                        headers={
                            "Content-Type": "application/json",
                            "ngrok-skip-browser-warning": "true",
                        },
                    )

                print(f"  ← [MedicalID] Response status: {resp.status_code}")
                print(
                    f"  ← [MedicalID] Response content (truncated): {resp.text[:]}..."
                )
                if resp.status_code != 200:
                    error_detail = resp.text[:500]
                    print(f"❌ HTTP Error {resp.status_code}: {error_detail}")
                    return f'{{"error": "HTTP {resp.status_code}: {error_detail}"}}'

                data = resp.json()
                predictions = data.get("predictions", [])
                if not predictions:
                    return '{"error": "No predictions in HTTP response"}'

                first = predictions[0]
                if isinstance(first, dict):
                    choices = first.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content")
                        if content:
                            raw = content
                        else:
                            raw = (
                                first.get("content")
                                or first.get("text")
                                or json.dumps(first)
                            )
                    else:
                        raw = (
                            first.get("content")
                            or first.get("text")
                            or json.dumps(first)
                        )
                else:
                    raw = str(first)

            except httpx.TimeoutException:
                print("❌ [MedicalID] HTTP timeout on text-only call")
                return '{"error": "Request timeout"}'
            except Exception as e:
                print(f"❌ [MedicalID] HTTP error on text-only call: {e}")
                return f'{{"error": "{str(e)}"}}'
        else:
            # Vertex AI mode
            response = self.endpoint.predict(instances=instances)
            raw = response.predictions[0] if response.predictions else ""

        # Remove thinking tokens
        clean = re.sub(r"<unused\d+>.*?<unused\d+>\s*", "", raw, flags=re.DOTALL)
        clean = re.sub(r"<unused\d+>", "", clean).strip()

        return clean

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        import re
        from json_repair import repair_json

        # Remove markdown code blocks
        response = re.sub(r"```json\s*", "", response)
        response = re.sub(r"```\s*", "", response)
        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to repair JSON
            try:
                repaired = repair_json(response)
                return json.loads(repaired)
            except Exception as e:
                print(f"⚠️  JSON parsing failed: {e}")
                return {}
