"""Timeline and audit models."""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Float, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class TimelineEvent(Base):
    """
    Timeline events for chronological visualization.
    Extracted from agent_context.temporal_events
    """

    __tablename__ = "timeline_events"

    id = Column(String, primary_key=True)
    document_id = Column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Event details
    event_date = Column(DateTime, nullable=False)
    event_type = Column(
        String, nullable=False
    )  # diagnosis, medication, procedure, lab_result, visit
    event_title = Column(String, nullable=False)
    event_description = Column(Text, nullable=True)

    # Related entity IDs (for drill-down)
    related_condition_id = Column(String, nullable=True)
    related_medication_id = Column(String, nullable=True)
    related_procedure_id = Column(String, nullable=True)
    related_lab_result_id = Column(String, nullable=True)

    # Importance for filtering
    importance = Column(String, nullable=True)  # high, medium, low

    # Additional context
    provider = Column(String, nullable=True)
    facility = Column(String, nullable=True)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    document = relationship("Document", back_populates="timeline_events")
    user = relationship("User", back_populates="timeline_events")
    embedding = relationship(
        "TimelineEventEmbedding",
        back_populates="timeline_event",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        Index("idx_timeline_document_id", "document_id"),
        Index("idx_timeline_user_id", "user_id"),
        Index("idx_timeline_event_date", "event_date"),
        Index("idx_timeline_event_type", "event_type"),
        Index("idx_timeline_importance", "importance"),
        Index("idx_timeline_deleted_at", "deleted_at"),
    )


class AuditLog(Base):
    """
    Audit trail for all document processing and data changes.
    """

    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )

    # Action details
    action = Column(String, nullable=False)  # upload, process, update, delete, view
    entity_type = Column(String, nullable=True)  # document, condition, medication, etc.
    entity_id = Column(String, nullable=True)

    # Changes (before/after for updates)
    changes = Column(JSON, nullable=True)

    # Context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_user_id", "user_id"),
        Index("idx_audit_document_id", "document_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_timestamp", "timestamp"),
    )


class SearchTerm(Base):
    """
    Search terms extracted from agent_context.semantic_keywords
    for fast full-text search.
    """

    __tablename__ = "search_terms"

    id = Column(String, primary_key=True)
    document_id = Column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )

    # Search data
    term = Column(String, nullable=False, index=True)
    term_type = Column(
        String, nullable=True
    )  # condition, medication, symptom, procedure
    relevance_score = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="search_terms")

    __table_args__ = (
        Index("idx_search_document_id", "document_id"),
        Index("idx_search_term", "term"),
        Index("idx_search_term_type", "term_type"),
    )
