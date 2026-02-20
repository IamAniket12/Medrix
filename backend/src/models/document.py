"""Document model."""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from .base import Base


class Document(Base):
    """Document model for uploaded medical documents."""

    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, nullable=False)

    # Document metadata
    document_type = Column(String, nullable=True)  # lab_report, prescription, etc.
    document_date = Column(DateTime, nullable=True)

    # AI extraction
    extraction_status = Column(
        String, default="pending", nullable=False
    )  # pending, processing, completed, failed
    extracted_data = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="documents")

    # Agent processing relationships
    processing_result = relationship(
        "DocumentProcessingResult",
        back_populates="document",
        cascade="all, delete-orphan",
        uselist=False,
    )
    summary = relationship(
        "DocumentSummary",
        back_populates="document",
        cascade="all, delete-orphan",
        uselist=False,
    )

    # Clinical data relationships
    conditions = relationship(
        "ClinicalCondition", back_populates="document", cascade="all, delete-orphan"
    )
    medications = relationship(
        "ClinicalMedication", back_populates="document", cascade="all, delete-orphan"
    )
    allergies = relationship(
        "ClinicalAllergy", back_populates="document", cascade="all, delete-orphan"
    )
    lab_results = relationship(
        "ClinicalLabResult", back_populates="document", cascade="all, delete-orphan"
    )
    vital_signs = relationship(
        "ClinicalVitalSign", back_populates="document", cascade="all, delete-orphan"
    )
    procedures = relationship(
        "ClinicalProcedure", back_populates="document", cascade="all, delete-orphan"
    )
    immunizations = relationship(
        "ClinicalImmunization", back_populates="document", cascade="all, delete-orphan"
    )
    timeline_events = relationship(
        "TimelineEvent", back_populates="document", cascade="all, delete-orphan"
    )
    search_terms = relationship(
        "SearchTerm", back_populates="document", cascade="all, delete-orphan"
    )
    embeddings = relationship(
        "DocumentEmbedding", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_document_user_id", "user_id"),
        Index("idx_document_type", "document_type"),
        Index("idx_document_date", "document_date"),
    )
