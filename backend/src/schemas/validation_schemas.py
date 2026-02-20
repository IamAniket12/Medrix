"""
Pydantic validation schemas for medical document processing.
Industry-grade validation with strict constraints and custom validators.
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator, field_validator
from enum import Enum
from datetime import datetime
import re


# ============================================================
# ENUMS AND BASE MODELS
# ============================================================


class DocumentType(str, Enum):
    """Valid medical document types."""

    PRESCRIPTION = "prescription"
    LAB_REPORT = "lab_report"
    CONSULTATION_NOTE = "consultation_note"
    DISCHARGE_SUMMARY = "discharge_summary"
    IMAGING_REPORT = "imaging_report"
    PROCEDURE_NOTE = "procedure_note"
    UNKNOWN = "unknown"


class Provider(BaseModel):
    """Provider information structure."""

    name: Optional[str] = None
    specialty: Optional[str] = None


# ============================================================
# DOCUMENT VALIDATION SCHEMAS
# ============================================================


class Processability(BaseModel):
    """Document processability metadata."""

    can_extract_text: bool = Field(
        True, description="Whether text can be extracted from document"
    )
    estimated_confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in text extraction quality (0.0-1.0)",
    )
    language: str = Field(
        "en",
        min_length=2,
        max_length=5,
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$",
        description="ISO 639-1 language code (e.g., 'en', 'es', 'en-US')",
    )

    @validator("estimated_confidence")
    def round_confidence(cls, v):
        """Round confidence to 2 decimal places."""
        return round(v, 2)

    @validator("language")
    def validate_language(cls, v):
        """Ensure language is lowercase ISO code."""
        return v.lower()

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "can_extract_text": True,
                "estimated_confidence": 0.95,
                "language": "en",
            }
        }


class ValidationResult(BaseModel):
    """Validated response from document validator agent."""

    is_valid: bool = Field(
        ..., description="Whether document is valid medical document with readable text"
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Document quality score: 0.0 (poor) to 1.0 (excellent)",
    )
    issues: List[str] = Field(
        default_factory=list,
        description="List of validation issues if any",
        max_items=20,
    )

    @validator("quality_score")
    def quality_score_precision(cls, v):
        """Round quality score to 2 decimal places."""
        return round(v, 2)

    @validator("issues")
    def validate_issues(cls, v, values):
        """Ensure issues exist only when is_valid is False."""
        is_valid = values.get("is_valid")
        if is_valid and len(v) > 0:
            raise ValueError("Valid documents should not have issues")
        if not is_valid and len(v) == 0:
            return ["Document validation failed"]
        return v

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {"is_valid": True, "quality_score": 0.95, "issues": []}
        }


class DocumentMetadata(BaseModel):
    """Document metadata from validator."""

    document_type: Union[DocumentType, str] = Field(
        ..., description="Type of medical document from predefined enum"
    )
    document_subtype: Optional[str] = Field(
        None,
        max_length=100,
        description="Document subtype if applicable (e.g., 'Progress Note', 'CBC Panel')",
    )
    document_date: Optional[str] = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Document date in YYYY-MM-DD format",
        example="2024-01-15",
    )
    document_source: Optional[str] = Field(
        None, max_length=200, description="Source of document (hospital, clinic name)"
    )
    provider: Optional[Provider] = Field(
        None, description="Healthcare provider information"
    )

    @validator("document_type", pre=True)
    def normalize_document_type(cls, v):
        """Normalize LLM variations to enum values."""
        # If already an enum, return as-is
        if isinstance(v, DocumentType):
            return v

        if isinstance(v, str):
            # Mapping of common LLM variations to canonical enum values
            normalization_map = {
                "laboratory_report": "lab_report",
                "lab report": "lab_report",
                "consultation note": "consultation_note",
                "discharge summary": "discharge_summary",
                "imaging report": "imaging_report",
                "procedure note": "procedure_note",
            }

            # Normalize: lowercase and replace underscores with spaces
            v_normalized = v.lower().replace("_", " ")

            # Return mapped canonical value, Pydantic will convert to enum
            return normalization_map.get(v_normalized, v)

    @validator("document_date")
    def validate_date_format(cls, v):
        """Validate date format is YYYY-MM-DD."""
        if v is None:
            return v
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError(f"Date must be in YYYY-MM-DD format, got: {v}")
        # Validate it's a real date
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date: {v} - {str(e)}")
        return v

    class Config:
        validate_assignment = True


class ValidationResponse(BaseModel):
    """Complete validation agent response."""

    validation: ValidationResult
    document_metadata: DocumentMetadata
    processability: Processability


# ============================================================
# CLINICAL DATA EXTRACTION SCHEMAS
# ============================================================


class ClinicalCondition(BaseModel):
    """Validated clinical condition."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Condition name (e.g., 'Type 2 Diabetes Mellitus')",
    )
    icd10_code: Optional[str] = Field(
        None,
        pattern=r"^[A-Z]\d{2}(\.\d{1,4})?$",
        description="ICD-10 code (e.g., 'E11.9', 'I10')",
        example="E11.9",
    )
    status: Optional[str] = Field(
        None,
        pattern=r"^(active|resolved|history_of|chronic|acute)$",
        description="Condition status: active, resolved, history_of, chronic, acute",
    )
    diagnosed_date: Optional[str] = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Date diagnosed in YYYY-MM-DD format",
    )
    severity: Optional[str] = Field(
        None,
        pattern=r"^(mild|moderate|severe|critical)$",
        description="Condition severity: mild, moderate, severe, critical",
    )
    body_site: Optional[str] = Field(
        None, max_length=200, description="Anatomical location if applicable"
    )

    @validator("name")
    def clean_name(cls, v):
        """Clean and normalize condition name."""
        return v.strip()

    class Config:
        validate_assignment = True


class ClinicalMedication(BaseModel):
    """Validated medication."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Medication name (generic or brand)",
    )
    dosage: Optional[str] = Field(
        None, max_length=100, description="Dosage (e.g., '500mg', '10mg/5ml')"
    )
    frequency: Optional[str] = Field(
        None,
        max_length=200,
        description="Frequency (e.g., 'twice daily', 'every 6 hours')",
    )
    route: Optional[str] = Field(
        None,
        pattern=r"^(oral|IV|IM|subcutaneous|topical|inhalation|rectal|sublingual|transdermal|ophthalmic|otic|nasal|other)$",
        description="Route of administration",
    )
    status: Optional[str] = Field(
        "active",
        pattern=r"^(active|started|continued|changed|stopped|discontinued)$",
        description="Medication status",
    )

    @validator("name")
    def clean_name(cls, v):
        """Clean and normalize medication name."""
        return v.strip()

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "name": "Metformin",
                "dosage": "500mg",
                "frequency": "twice daily",
                "route": "oral",
                "status": "active",
            }
        }


class ClinicalDataResponse(BaseModel):
    """Complete clinical extraction response."""

    conditions: List[ClinicalCondition] = Field(default_factory=list)
    medications: List[ClinicalMedication] = Field(default_factory=list)
    allergies: List[Dict[str, Any]] = Field(default_factory=list)
    lab_results: List[Dict[str, Any]] = Field(default_factory=list)
    vital_signs: List[Dict[str, Any]] = Field(default_factory=list)
    procedures: List[Dict[str, Any]] = Field(default_factory=list)
    immunizations: List[Dict[str, Any]] = Field(default_factory=list)


# ============================================================
# SUMMARY SCHEMAS
# ============================================================


class DetailedSummary(BaseModel):
    """Detailed summary structure."""

    clinical_overview: str = ""
    key_findings: List[str] = Field(default_factory=list)
    treatment_plan: Dict[str, Any] = Field(default_factory=dict)
    clinical_significance: str = ""
    action_items: List[str] = Field(default_factory=list)


class SummaryResponse(BaseModel):
    """Complete summary response with validation."""

    brief_summary: str = Field(
        default="Summary extraction failed - document could not be summarized",
        description="Comprehensive 5-7 sentence human-readable summary covering all key information",
    )
    search_optimized_summary: str = Field(
        default="Search optimization failed - embeddings may not work correctly for this document",
        description="Comprehensive 400-600 word search-optimized summary with exhaustive medical terminology for embeddings",
    )
    urgency_level: str = Field(
        default="routine", pattern="^(routine|follow-up-needed|urgent|critical)$"
    )
    detailed_summary: DetailedSummary = Field(default_factory=DetailedSummary)
    agent_context: Dict[str, Any] = Field(default_factory=dict)

    @validator("brief_summary", pre=True, always=True)
    def validate_brief_summary(cls, v):
        if not v or len(v.strip()) == 0:
            return "No summary available - document could not be processed"
        # Detect and reject the old misleading default
        if v.strip() in ("Document processed successfully", "Document processed"):
            print(
                "⚠️  Agent 3 returned placeholder default - LLM likely failed or JSON parse failed"
            )
            return "Summary extraction failed - LLM did not return a valid response"
        if len(v.strip()) < 100:
            print(
                f"⚠️  Brief summary too short ({len(v)} chars) - should be 5-7 comprehensive sentences"
            )
        return v

    @validator("search_optimized_summary", pre=True, always=True)
    def validate_search_summary(cls, v):
        if not v or len(v.strip()) == 0:
            return "Document summary not available - extraction failed"
        # Detect and reject the old misleading default
        if v.strip() in ("Document processed successfully", "Document processed"):
            return "Search optimization failed - LLM did not return a valid response"
        if len(v.strip()) < 300:
            print(
                f"⚠️  Search summary too short ({len(v)} chars) - should be 400-600 words with exhaustive terminology"
            )
        return v
