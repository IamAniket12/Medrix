"""Database models for vector embeddings."""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime

from .base import Base, TimestampMixin


class DocumentEmbedding(Base, TimestampMixin):
    """Store document embeddings for RAG-based retrieval."""

    __tablename__ = "document_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(255), nullable=False, index=True)

    # Content and metadata
    chunk_text = Column(Text, nullable=False)  # Text chunk from document
    chunk_index = Column(Integer, nullable=False)  # Position in document

    # Vector embedding (using Google's textembedding-gecko@003, 768 dimensions)
    embedding = Column(Vector(768), nullable=False)

    # Metadata for better retrieval
    document_type = Column(String(100))  # lab_report, prescription, etc.
    document_date = Column(DateTime)  # Date from document

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="embeddings")

    __table_args__ = (
        Index("idx_document_embeddings_user", "user_id"),
        Index("idx_document_embeddings_document", "document_id"),
        Index(
            "idx_document_embeddings_vector", "embedding", postgresql_using="ivfflat"
        ),
    )


class TimelineEventEmbedding(Base, TimestampMixin):
    """Store timeline event embeddings for temporal context retrieval."""

    __tablename__ = "timeline_event_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        String,
        ForeignKey("timeline_events.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id = Column(String(255), nullable=False, index=True)

    # Event summary for embedding
    event_summary = Column(Text, nullable=False)

    # Vector embedding (768 dimensions)
    embedding = Column(Vector(768), nullable=False)

    # Event metadata
    event_type = Column(String(100))
    event_date = Column(DateTime)
    importance = Column(String(50))

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    timeline_event = relationship("TimelineEvent", back_populates="embedding")

    __table_args__ = (
        Index("idx_timeline_embeddings_user", "user_id"),
        Index("idx_timeline_embeddings_event", "event_id"),
        Index(
            "idx_timeline_embeddings_vector", "embedding", postgresql_using="ivfflat"
        ),
    )


class ClinicalEntityEmbedding(Base, TimestampMixin):
    """Store embeddings for clinical entities (medications, conditions, labs) for relationship mapping."""

    __tablename__ = "clinical_entity_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)

    # Entity identification
    entity_type = Column(
        String(100), nullable=False
    )  # medication, condition, lab_result, procedure
    entity_id = Column(String, nullable=False)  # ID in respective table
    entity_name = Column(String(500), nullable=False)

    # Entity summary for embedding
    entity_summary = Column(Text, nullable=False)

    # Vector embedding (768 dimensions)
    embedding = Column(Vector(768), nullable=False)

    # Metadata
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_clinical_embeddings_user", "user_id"),
        Index("idx_clinical_embeddings_type", "entity_type"),
        Index("idx_clinical_embeddings_entity", "entity_type", "entity_id"),
        Index(
            "idx_clinical_embeddings_vector", "embedding", postgresql_using="ivfflat"
        ),
    )
