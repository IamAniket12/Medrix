"""Database models."""

from .base import Base
from .user import User
from .document import Document

# Agent processing models
from .document_processing import DocumentProcessingResult, DocumentSummary

# Clinical data models
from .clinical_data import (
    ClinicalCondition,
    ClinicalMedication,
    ClinicalAllergy,
    ClinicalLabResult,
    ClinicalVitalSign,
    ClinicalProcedure,
    ClinicalImmunization,
)

# Timeline and audit models
from .timeline import TimelineEvent, AuditLog, SearchTerm

# Vector embeddings for RAG
from .embeddings import (
    DocumentEmbedding,
    TimelineEventEmbedding,
    ClinicalEntityEmbedding,
)

__all__ = [
    "Base",
    "User",
    "Document",
    # Processing models
    "DocumentProcessingResult",
    "DocumentSummary",
    # Clinical data models
    "ClinicalCondition",
    "ClinicalMedication",
    "ClinicalAllergy",
    "ClinicalLabResult",
    "ClinicalVitalSign",
    "ClinicalProcedure",
    "ClinicalImmunization",
    # Timeline and audit
    "TimelineEvent",
    "AuditLog",
    "SearchTerm",
    # Embeddings
    "DocumentEmbedding",
    "TimelineEventEmbedding",
    "ClinicalEntityEmbedding",
]
