"""User model."""

from sqlalchemy import Column, String, Date
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User model for authentication (Phase 2)."""

    __tablename__ = "users"

    id = Column(String, primary_key=True)  # CUID from frontend
    email = Column(String, unique=True, nullable=True, index=True)
    name = Column(String, nullable=True)

    # Demographics for Medical ID
    date_of_birth = Column(Date, nullable=True)
    blood_type = Column(String, nullable=True)  # A+, A-, B+, B-, AB+, AB-, O+, O-
    gender = Column(String, nullable=True)  # male, female, other, prefer-not-to-say
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    primary_care_physician = Column(String, nullable=True)

    # Relationships
    documents = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan"
    )

    # Clinical data relationships
    conditions = relationship(
        "ClinicalCondition", back_populates="user", cascade="all, delete-orphan"
    )
    medications = relationship(
        "ClinicalMedication", back_populates="user", cascade="all, delete-orphan"
    )
    allergies = relationship(
        "ClinicalAllergy", back_populates="user", cascade="all, delete-orphan"
    )
    lab_results = relationship(
        "ClinicalLabResult", back_populates="user", cascade="all, delete-orphan"
    )
    vital_signs = relationship(
        "ClinicalVitalSign", back_populates="user", cascade="all, delete-orphan"
    )
    procedures = relationship(
        "ClinicalProcedure", back_populates="user", cascade="all, delete-orphan"
    )
    immunizations = relationship(
        "ClinicalImmunization", back_populates="user", cascade="all, delete-orphan"
    )
    timeline_events = relationship(
        "TimelineEvent", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship("AuditLog", back_populates="user")

    # Medical ID relationships
    medical_id_cards = relationship(
        "MedicalIDCard", back_populates="user", cascade="all, delete-orphan"
    )
    temporary_medical_summaries = relationship(
        "TemporaryMedicalSummary", back_populates="user", cascade="all, delete-orphan"
    )
