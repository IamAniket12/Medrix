"""
MedGemma service for medical document analysis.

Supports two backends (selected automatically via environment variables):
  - Colab / generic HTTP  : set MEDGEMMA_ENDPOINT_URL=https://<ngrok-or-other-url>
  - Vertex AI (default)   : set GOOGLE_CLOUD_PROJECT + MEDGEMMA_ENDPOINT_ID
"""

import base64
import logging
from typing import Dict, Any, List, Optional
from src.core.config import Settings

try:
    from google.cloud import aiplatform as _aiplatform
except ImportError:
    _aiplatform = None  # type: ignore

logger = logging.getLogger(__name__)


class MedGemmaService:
    """Service for interacting with MedGemma (Vertex AI or Colab HTTP)."""

    def __init__(self, settings: Settings):
        """
        Initialize MedGemma service.

        If ``MEDGEMMA_ENDPOINT_URL`` is set the service forwards requests to
        that HTTP endpoint (e.g. a Google Colab + ngrok deployment) instead of
        Vertex AI.  All other behaviour and return shapes are identical.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self._initialized = False
        self.endpoint = None  # Vertex AI Endpoint object (None in HTTP mode)

        # ── HTTP / Colab mode ─────────────────────────────────────────────
        http_url: Optional[str] = getattr(settings, "medgemma_endpoint_url", None)
        if http_url:
            self._mode = "http"
            self._http_url = http_url.rstrip("/")
            self._initialized = True
            logger.info("[OK] MedGemma service → HTTP / Colab mode")
            logger.info(f"  Endpoint URL : {self._http_url}")
            return

        # ── Vertex AI mode (default) ──────────────────────────────────────
        self._mode = "vertex"
        self.project = settings.google_cloud_project
        self.location = settings.vertex_ai_location
        self.endpoint_id = settings.medgemma_endpoint_id

        if _aiplatform is None:
            logger.warning(
                "[WARN] google-cloud-aiplatform not installed; MedGemma will use mock responses."
            )
            return

        try:
            endpoint_resource_name = (
                f"projects/{self.project}/locations/{self.location}"
                f"/endpoints/{self.endpoint_id}"
            )
            self.endpoint = _aiplatform.Endpoint(endpoint_name=endpoint_resource_name)
            self._initialized = True
            logger.info("[OK] MedGemma service initialized (Vertex AI)")
            logger.info(f"  Project    : {self.project}")
            logger.info(f"  Location   : {self.location}")
            logger.info(f"  Endpoint ID: {self.endpoint_id[:20]}...")
        except Exception as e:
            logger.error(
                f"[ERR] Could not initialize MedGemma service: {e}", exc_info=True
            )
            logger.warning("   MedGemma service will return error responses.")
            self._initialized = False

    def encode_image(self, image_path: str) -> str:
        """
        Encode image file to base64 string.

        Args:
            image_path: Path to the image file

        Returns:
            Base64 encoded image string
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    async def predict(
        self, image_path: str, prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send image to MedGemma for inference.

        Routes to HTTP (Colab) or Vertex AI depending on configuration.
        Returns mock data when neither is available.

        Args:
            image_path: Path to the image file
            prompt: Optional custom prompt for the model

        Returns:
            Dictionary containing model predictions
        """
        if not self._initialized:
            return self._get_mock_response()

        # Encode image + resolve prompt
        image_b64 = self.encode_image(image_path)
        if not prompt:
            prompt = self._get_default_prompt()

        instances = [{"prompt": prompt, "image": {"bytesBase64Encoded": image_b64}}]

        # ── HTTP / Colab path ─────────────────────────────────────────────
        if self._mode == "http":
            return await self._call_http_endpoint(instances)

        # ── Vertex AI path ────────────────────────────────────────────────
        try:
            response = self.endpoint.predict(instances=instances)
            return {
                "success": True,
                "predictions": response.predictions,
                "deployed_model_id": response.deployed_model_id,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _call_http_endpoint(self, instances: list) -> Dict[str, Any]:
        """
        POST ``instances`` to the Colab / generic HTTP MedGemma endpoint.

        Returns a dict in the same shape as the Vertex AI predict() response so
        the rest of the service code is unchanged.
        """
        import httpx

        payload = {"instances": instances}
        try:
            # Increased timeout to 300s for HPC with 8192 max tokens
            async with httpx.AsyncClient(timeout=300.0) as client:
                logger.info(
                    f"[MedGemma HTTP] Sending request with {len(instances)} instance(s)"
                )
                resp = await client.post(
                    f"{self._http_url}/predict",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        # Required to bypass ngrok's browser-warning splash page
                        "ngrok-skip-browser-warning": "true",
                    },
                )
            resp.raise_for_status()
            data = resp.json()
            logger.info(
                f"[MedGemma HTTP] Success - {len(data.get('predictions', []))} predictions returned"
            )
            return {
                "success": True,
                "predictions": data.get("predictions", []),
                "deployed_model_id": data.get("deployed_model_id", "colab"),
            }
        except Exception as e:
            logger.error(f"[ERR] HTTP endpoint call failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def analyze_document(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a medical document and extract structured information.

        Args:
            file_path: Path to the document (image or converted PDF)

        Returns:
            Extracted medical information
        """
        result = await self.predict(file_path)

        if not result["success"]:
            return result

        # Parse predictions
        predictions = result.get("predictions", [])

        if not predictions:
            return {"success": False, "error": "No predictions returned from model"}

        # Extract structured data from first prediction
        prediction = predictions[0]

        return {
            "success": True,
            "extracted_data": {
                "raw_output": prediction,
                "text": self._extract_text(prediction),
                "labels": self._extract_labels(prediction),
                "summary": self._extract_summary(prediction),
            },
        }

    def _get_default_prompt(self) -> str:
        """Get default extraction prompt for medical documents."""
        return """Analyze this medical document and extract the following information:

1. Document Type (e.g., lab report, prescription, X-ray, discharge summary)
2. Patient Information (name, age, date of birth if visible)
3. Date of document
4. Medical findings, diagnoses, or conditions
5. Medications mentioned (name, dosage, frequency)
6. Allergies mentioned
7. Test results (if applicable)
8. Provider/Doctor information
9. A brief summary of the document

Please provide the information in a structured format."""

    def _extract_text(self, prediction: Any) -> str:
        """
        Extract text content from prediction.

        Args:
            prediction: Model prediction output

        Returns:
            Extracted text string
        """
        if isinstance(prediction, dict):
            return prediction.get("text", str(prediction))
        return str(prediction)

    def _extract_labels(self, prediction: Any) -> List[str]:
        """
        Extract labels/categories from prediction.

        Args:
            prediction: Model prediction output

        Returns:
            List of extracted labels
        """
        if isinstance(prediction, dict):
            return prediction.get("labels", [])
        return []

    def _extract_summary(self, prediction: Any) -> str:
        """
        Extract summary from prediction.

        Args:
            prediction: Model prediction output

        Returns:
            Extracted summary string
        """
        if isinstance(prediction, dict):
            return prediction.get("summary", "")
        return ""

    def _get_mock_response(self) -> Dict[str, Any]:
        """
        Return mock response for development without Google Cloud credentials.

        Returns:
            Mock prediction response
        """
        return {
            "success": True,
            "predictions": [
                {
                    "text": "**Document Type:** Lab Report\\n\\n**Patient Information:**\\n- Name: [Redacted for privacy]\\n- Age: Not visible\\n- DOB: Not visible\\n\\n**Date:** [Sample Date]\\n\\n**Medical Findings:**\\nThis is a sample lab report for development purposes.\\n\\n**Test Results:**\\n- Sample Test 1: Normal\\n- Sample Test 2: Normal\\n\\n**Summary:** This is mock data returned because Google Cloud credentials are not configured. Configure GOOGLE_APPLICATION_CREDENTIALS in .env file to use real MedGemma API.",
                    "labels": ["lab_report", "test_results"],
                    "summary": "Mock lab report data for development. Configure Google Cloud credentials to analyze real medical documents.",
                }
            ],
            "deployed_model_id": "mock_model",
            "mock": True,
        }

    async def generate_text_response(self, prompt: str) -> Dict[str, Any]:
        """
        Generate text response from MedGemma for medical Q&A tasks using chatCompletions format.

        Returns a structured dict with `text` and optional `structured` (parsed JSON) keys.
        """
        # Return mock response if not initialized
        if not self._initialized:
            return self._get_mock_qa_response(prompt)

        try:
            system_instruction = (
                "You are a medical information assistant. Respond ONLY with a single JSON object and nothing else. "
                'Schema: {"answer": string, "key_details": [string], "citations": [string], "note": string}. '
                "Do not include any explanations, thoughts, analysis, markdown, or additional text. "
                "If information is missing, set answer to an empty string and describe missing info in note."
            )

            instances = [
                {
                    "@requestFormat": "chatCompletions",
                    "messages": [
                        {
                            "role": "system",
                            "content": [{"type": "text", "text": system_instruction}],
                        },
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": prompt}],
                        },
                    ],
                    "max_tokens": 320,
                    "temperature": 0.2,
                }
            ]

            # ── HTTP / Colab path ─────────────────────────────────────────
            if self._mode == "http":
                http_result = await self._call_http_endpoint(instances)
                if not http_result.get("success"):
                    return http_result
                predictions = http_result.get("predictions", [])
                content_text = None
                if predictions:
                    first = predictions[0]
                    if isinstance(first, dict):
                        choices = first.get("choices", [])
                        if choices:
                            content_text = choices[0].get("message", {}).get("content")
                        if not content_text:
                            content_text = first.get("content") or first.get("text")
                if not content_text:
                    return {"success": False, "error": "No content in HTTP response"}
                # Skip into the JSON-parsing block below
            else:
                # ── Vertex AI path ─────────────────────────────────────────
                logger.info("🔍 Calling MedGemma endpoint for chatCompletions...")
                response = self.endpoint.predict(instances=instances)

                predictions = response.predictions
                logger.info(f"📥 Response predictions type: {type(predictions)}")

                if isinstance(predictions, dict) and "error" in predictions:
                    error_msg = predictions["error"].get(
                        "message", str(predictions["error"])
                    )
                    logger.error(f"❌ MedGemma returned error: {error_msg}")
                    return {"success": False, "error": error_msg}

                if isinstance(predictions, list) and len(predictions) > 0:
                    result = predictions[0]
                    while isinstance(result, list) and len(result) > 0:
                        result = result[0]
                else:
                    result = predictions

                content_text = None
                if isinstance(result, dict):
                    if "candidates" in result and result["candidates"]:
                        candidate = result["candidates"][0]
                        content_parts = candidate.get("content", {}).get(
                            "parts"
                        ) or candidate.get("content", [])
                        if isinstance(content_parts, list):
                            text_parts = [
                                p.get("text")
                                for p in content_parts
                                if isinstance(p, dict) and p.get("text")
                            ]
                            content_text = (
                                "\n".join([t for t in text_parts if t])
                                if text_parts
                                else None
                            )
                    if not content_text:
                        content_text = (
                            result.get("content")
                            or result.get("text")
                            or result.get("message", {}).get("content")
                            or result.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content")
                        )
                elif isinstance(result, str):
                    content_text = result

            if not content_text:
                logger.error("❌ No content found in MedGemma response")
                return {
                    "success": False,
                    "error": "No content found in response",
                }

            content_text = content_text.strip()

            # Remove leading "thought" or analysis preamble before attempting JSON parsing
            def _strip_thought_prefix(text: str) -> str:
                lower = text.lower()
                if lower.startswith("thought") or lower.startswith("analysis"):
                    # If a JSON object follows, keep from first '{'
                    if "{" in text:
                        return text[text.find("{") :].strip()
                    # Otherwise drop the first line
                    parts = text.split("\n", 1)
                    return parts[1].strip() if len(parts) > 1 else text
                return text

            content_text = _strip_thought_prefix(content_text)

            # Normalize to JSON payload if model wrapped with prose/thoughts/code fences
            def _extract_json_block(text: str) -> Optional[str]:
                if "```json" in text:
                    after_fence = text.split("```json", 1)[1]
                    if "```" in after_fence:
                        return after_fence.split("```", 1)[0].strip()
                if "{" in text and "}" in text:
                    return text[text.find("{") : text.rfind("}") + 1].strip()
                return None

            # Attempt to parse JSON as instructed
            structured = None
            import json

            # Try direct JSON load first
            try:
                structured = json.loads(content_text)
            except Exception:
                extracted = _extract_json_block(content_text)
                if extracted:
                    try:
                        structured = json.loads(extracted)
                    except Exception:
                        structured = None

            if not structured:
                logger.error("❌ Model did not return JSON; rejecting response")
                return {
                    "success": False,
                    "error": "Model returned non-JSON response",
                }

            # Validate structured JSON shape
            required_keys = {"answer", "key_details", "citations", "note"}
            if not isinstance(structured, dict) or not required_keys.issubset(
                structured.keys()
            ):
                logger.warning(
                    "⚠️ Structured response missing required keys; returning raw text"
                )
                return {
                    "success": True,
                    "text": content_text,
                    "confidence": 0.85,
                    "model": "medgemma",
                }

            # Normalize structured fields to expected types
            key_details = structured.get("key_details") or []
            citations = structured.get("citations") or []
            note = structured.get("note") or ""
            if not isinstance(key_details, list):
                key_details = [str(key_details)]
            if not isinstance(citations, list):
                citations = [str(citations)]
            structured["key_details"] = [str(item).strip() for item in key_details]
            structured["citations"] = [str(item).strip() for item in citations]
            structured["note"] = str(note).strip()

            logger.info("✓ Parsed structured JSON response from MedGemma")
            return {
                "success": True,
                "text": structured.get("answer", ""),
                "structured": structured,
                "confidence": 0.9,
                "model": "medgemma",
            }

        except Exception as e:
            logger.error(f"❌ Error generating text response: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _get_mock_qa_response(self, prompt: str) -> Dict[str, Any]:
        """
        Generate mock Q&A response by intelligently parsing the medical context.
        Simulates RAG-based medical AI: reads embedded chunks and synthesizes an answer.

        This is a fallback for development/testing when MedGemma is unavailable.

        Args:
            prompt: The complete RAG prompt with medical records and question

        Returns:
            Mock response dictionary with synthesized answer
        """
        import re

        # Extract question from prompt
        question_marker = "=== PATIENT'S QUESTION ==="
        if question_marker in prompt:
            question = prompt.split(question_marker)[1].split("===")[0].strip()
        else:
            question = "your question"

        # Extract medical context from prompt (the embedded chunks)
        context_marker = "=== PATIENT'S MEDICAL RECORDS ==="
        chunks = []
        source_info = []

        if context_marker in prompt and question_marker in prompt:
            context_section = prompt.split(context_marker)[1].split(question_marker)[0]

            # Extract all chunks with their source information
            for source_block in context_section.split("[Source")[1:]:
                lines = source_block.strip().split("\\n")

                # Parse source header
                source_header = lines[0] if lines else ""
                doc_type = ""
                filename = ""
                date = ""

                if ":" in source_header:
                    parts = source_header.split(":")
                    doc_type = parts[0].split("]")[1].strip() if "]" in parts[0] else ""
                    filename = parts[1].strip() if len(parts) > 1 else ""

                # Parse metadata line
                if len(lines) > 1 and "Date:" in lines[1]:
                    date_match = re.search(r"Date:\\s*([^|]+)", lines[1])
                    if date_match:
                        date = date_match.group(1).strip()

                # Extract content (after "Content:" line)
                content_text = ""
                content_started = False
                for line in lines:
                    if "Content:" in line:
                        content_started = True
                        # Get text after "Content:"
                        content_text += line.split("Content:")[-1].strip() + " "
                    elif content_started and line.strip():
                        content_text += line.strip() + " "

                if content_text.strip():
                    chunks.append(content_text.strip())
                    source_info.append(
                        {"type": doc_type, "filename": filename, "date": date}
                    )

    def _get_mock_qa_response(self, prompt: str) -> Dict[str, Any]:
        """
        Mock response when MedGemma is unavailable.

        Industry practice: Don't hardcode answer generation with regex patterns.
        Either use a fallback LLM or return the context directly to the user.

        Args:
            prompt: The complete RAG prompt with medical records and question

        Returns:
            Mock response indicating service unavailable
        """
        return {
            "success": False,
            "text": "⚠️ MedGemma service is currently unavailable. Please configure Google Cloud credentials (GOOGLE_APPLICATION_CREDENTIALS in .env) to enable AI-powered medical question answering.",
            "confidence": 0.0,
            "mock": True,
            "model": "mock_medgemma",
            "error": "MedGemma endpoint not initialized. Configure Google Cloud to use this feature.",
        }

    def _analyze_summaries_and_answer(self, question: str, summaries: List[str]) -> str:
        """
        Analyze medical summaries and generate an answer.
        Uses regex patterns to dynamically extract information (no hardcoding).

        Args:
            question: User's question
            summaries: List of brief_summaries from retrieved documents

        Returns:
            Synthesized answer based on question type
        """
        import re

        question_lower = question.lower()
        answer_parts = ["Based on your medical records:\n"]

        # MEDICATION QUESTIONS
        if any(
            word in question_lower
            for word in ["medication", "medicine", "drug", "taking", "prescribed"]
        ):
            medications = []

            for summary in summaries:
                # Pattern 1: MedicationName Dosage (e.g., "Metformin 1000mg" or "Metformin 1000 milligrams")
                pattern1 = r"\b([A-Z][a-z]+(?:ol|in|ide|pril|ine|tin)?)\s+(\d+\s*(?:mg|milligrams?))"
                matches1 = re.finditer(pattern1, summary)
                for match in matches1:
                    medications.append(f"• **{match.group(1)}** {match.group(2)}")

                # Pattern 2: "starting/prescribed MedicationName"
                pattern2 = r"(?:start|prescrib)[a-z]*\s+([A-Z][a-z]+)"
                matches2 = re.finditer(pattern2, summary)
                for match in matches2:
                    med_name = match.group(1)
                    if med_name not in [
                        "Labs",
                        "Plan",
                        "Follow",
                    ]:  # Filter common words
                        medications.append(f"• **{med_name}**")

            if medications:
                # Deduplicate while preserving order
                seen = set()
                unique_meds = []
                for med in medications:
                    if med not in seen:
                        seen.add(med)
                        unique_meds.append(med)

                answer_parts.append("\n**Your current medications:**")
                answer_parts.extend(unique_meds[:5])  # Top 5
            else:
                answer_parts.append(
                    "\nNo specific medications were found in the available records."
                )

        # CONDITION/DIAGNOSIS QUESTIONS
        elif any(
            word in question_lower
            for word in [
                "condition",
                "diagnosis",
                "disease",
                "health",
                "diagnosed",
                "problem",
            ]
        ):
            conditions = []

            for summary in summaries:
                # Pattern: "Assessment includes X, Y, and Z" or "Suspected/Confirmed X"
                pattern1 = r"(?:Assessment|Diagnosis|includes?|Suspected|Confirmed)\s+([^.]+?)(?:,|and|\.|$)"
                matches = re.finditer(pattern1, summary, re.IGNORECASE)
                for match in matches:
                    condition_text = match.group(1).strip()
                    if 5 < len(condition_text) < 80:  # Reasonable length
                        conditions.append(f"• {condition_text}")

            if conditions:
                # Deduplicate
                unique_conditions = list(dict.fromkeys(conditions))
                answer_parts.append("\n**Your documented conditions:**")
                answer_parts.extend(unique_conditions[:5])
            else:
                answer_parts.append(
                    "\nNo specific conditions were documented in the available records."
                )

        # LAB/TEST QUESTIONS
        elif any(
            word in question_lower
            for word in ["lab", "test", "result", "blood", "hba1c"]
        ):
            labs = []

            for summary in summaries:
                # Pattern: Lab name followed by value
                patterns = [
                    (r"(HbA1c|A1C)[:\s]+(\d+\.?\d*%?)", "HbA1c"),
                    (r"(Blood pressure|BP)[:\s]+(\d+/\d+)", "Blood Pressure"),
                    (r"(Cholesterol|LDL|HDL|Triglycerides)[:\s]+(\d+)", None),
                ]

                for pattern, display_name in patterns:
                    matches = re.finditer(pattern, summary, re.IGNORECASE)
                    for match in matches:
                        name = display_name or match.group(1)
                        value = match.group(2)
                        labs.append(f"• **{name}:** {value}")

            if labs:
                unique_labs = list(dict.fromkeys(labs))
                answer_parts.append("\n**Your lab results:**")
                answer_parts.extend(unique_labs[:8])
            else:
                answer_parts.append(
                    "\nNo specific lab results were found in the available records."
                )

        # GENERAL QUESTIONS - show relevant excerpt
        else:
            if summaries:
                # Show most relevant summary (first 400 chars)
                excerpt = summaries[0][:400].strip()
                if len(summaries[0]) > 400:
                    excerpt += "..."
                answer_parts.append(f"\n{excerpt}")

        # Add disclaimer
        answer_parts.append(
            "\n\n⚠️ **Important:** This information is from your uploaded medical records. Always consult your healthcare provider for medical advice."
        )

        return "\n".join(answer_parts)
