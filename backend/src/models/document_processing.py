"""Document processing result models - stores raw agent outputs."""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    JSON,
    Float,
    Boolean,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class DocumentProcessingResult(Base):
    """
    Stores raw agent processing results for each document.
    This is the main table that captures all agent outputs in JSONB format.
    """

    __tablename__ = "document_processing_results"

    id = Column(String, primary_key=True)
    document_id = Column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    processing_started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_status = Column(
        String, nullable=False, default="processing"
    )  # processing, completed, failed

    # Validation results (Agent 1)
    validation_result = Column(JSON, nullable=True)  # Full validation output
    is_valid = Column(Boolean, nullable=True)
    quality_score = Column(Float, nullable=True)
    validation_issues = Column(JSON, nullable=True)  # Array of issues if invalid

    # Document metadata (extracted by Agent 1)
    document_metadata = Column(JSON, nullable=True)  # Full metadata object

    # Clinical data (Agent 2)
    clinical_data = Column(JSON, nullable=True)  # Full extraction output

    # Summaries (Agent 3)
    summaries = Column(JSON, nullable=True)  # Full summary output
    brief_summary = Column(Text, nullable=True)  # Extracted for quick access
    urgency_level = Column(
        String, nullable=True
    )  # routine, follow-up-needed, urgent, critical

    # Agent context for future agents
    agent_context = Column(JSON, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    document = relationship("Document", back_populates="processing_result")

    __table_args__ = (
        Index("idx_proc_document_id", "document_id"),
        Index("idx_proc_status", "processing_status"),
        Index("idx_proc_is_valid", "is_valid"),
        Index("idx_proc_urgency", "urgency_level"),
        Index("idx_proc_quality", "quality_score"),
    )


class DocumentSummary(Base):
    """
    Denormalized summary data for fast access.
    Extracted from DocumentProcessingResult for performance.
    """

    __tablename__ = "document_summaries"

    id = Column(String, primary_key=True)
    document_id = Column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Human-readable summaries
    brief_summary = Column(Text, nullable=True)
    search_optimized_summary = Column(
        Text, nullable=True
    )  # Agent 3 RAG-optimized text (used for embeddings)
    clinical_overview = Column(Text, nullable=True)
    clinical_significance = Column(Text, nullable=True)
    urgency_level = Column(String, nullable=True)

    # Key findings (array of strings)
    key_findings = Column(JSON, nullable=True)

    # Treatment plan
    treatment_plan = Column(
        JSON, nullable=True
    )  # medications_started/stopped, lifestyle, follow_up

    # Action items (array of strings)
    action_items = Column(JSON, nullable=True)

    # Agent context for future AI agents
    semantic_keywords = Column(JSON, nullable=True)  # Array of keywords
    clinical_relationships = Column(
        JSON, nullable=True
    )  # Array of condition-treatment mappings
    temporal_events = Column(JSON, nullable=True)  # Timeline data
    risk_factors = Column(JSON, nullable=True)  # Identified risks
    missing_information = Column(JSON, nullable=True)  # Data gaps

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    document = relationship("Document", back_populates="summary")

    __table_args__ = (
        Index("idx_summary_document_id", "document_id"),
        Index("idx_summary_urgency", "urgency_level"),
    )
