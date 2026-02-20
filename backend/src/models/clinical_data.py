"""Clinical data models - normalized tables for medical information."""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Float,
    Boolean,
    Text,
    Date,
    Integer,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class ClinicalCondition(Base):
    """
    Medical conditions/diagnoses extracted from documents.
    Normalized from Agent 2 clinical_data.conditions
    """

    __tablename__ = "clinical_conditions"

    id = Column(String, primary_key=True)
    document_id = Column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Core fields (from Agent 2 output)
    name = Column(String, nullable=False)
    status = Column(String, nullable=True)  # active, resolved, chronic, suspected
    diagnosed_date = Column(Date, nullable=True)
    severity = Column(String, nullable=True)  # mild, moderate, severe
    body_site = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Medical coding (for future integration)
    icd10_code = Column(String, nullable=True)
    snomed_code = Column(String, nullable=True)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    document = relationship("Document", back_populates="conditions")
    user = relationship("User", back_populates="conditions")

    __table_args__ = (
        Index("idx_condition_document_id", "document_id"),
        Index("idx_condition_user_id", "user_id"),
        Index("idx_condition_status", "status"),
        Index("idx_condition_deleted_at", "deleted_at"),
        Index("idx_condition_icd10", "icd10_code"),
    )


class ClinicalMedication(Base):
    """
    Medications extracted from documents.
    Normalized from Agent 2 clinical_data.medications
    """

    __tablename__ = "clinical_medications"

    id = Column(String, primary_key=True)
    document_id = Column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Core fields (from Agent 2 output)
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=True)
    frequency = Column(String, nullable=True)
    route = Column(String, nullable=True)  # oral, IV, topical, etc.
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    prescriber = Column(String, nullable=True)
    indication = Column(String, nullable=True)  # What it's treating
    notes = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Medical coding
    rxnorm_code = Column(String, nullable=True)
    ndc_code = Column(String, nullable=True)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    document = relationship("Document", back_populates="medications")
    user = relationship("User", back_populates="medications")

    __table_args__ = (
        Index("idx_medication_document_id", "document_id"),
        Index("idx_medication_user_id", "user_id"),
        Index("idx_medication_is_active", "is_active"),
        Index("idx_medication_deleted_at", "deleted_at"),
        Index("idx_medication_rxnorm", "rxnorm_code"),
    )


class ClinicalAllergy(Base):
    """
    Allergies and adverse reactions extracted from documents.
    Normalized from Agent 2 clinical_data.allergies
    """

    __tablename__ = "clinical_allergies"

    id = Column(String, primary_key=True)
    document_id = Column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Core fields (from Agent 2 output)
    allergen = Column(String, nullable=False)
    reaction = Column(String, nullable=True)
    severity = Column(String, nullable=True)  # mild, moderate, severe, life-threatening
    allergy_type = Column(String, nullable=True)  # drug, food, environmental
    verified_date = Column(Date, nullable=True)
    verified_by = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    document = relationship("Document", back_populates="allergies")
    user = relationship("User", back_populates="allergies")

    __table_args__ = (
        Index("idx_allergy_document_id", "document_id"),
        Index("idx_allergy_user_id", "user_id"),
        Index("idx_allergy_severity", "severity"),
        Index("idx_allergy_is_active", "is_active"),
        Index("idx_allergy_deleted_at", "deleted_at"),
    )


class ClinicalLabResult(Base):
    """
    Laboratory test results extracted from documents.
    Normalized from Agent 2 clinical_data.lab_results
    """

    __tablename__ = "clinical_lab_results"

    id = Column(String, primary_key=True)
    document_id = Column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Core fields (from Agent 2 output)
    test_name = Column(String, nullable=False)
    value = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    reference_range = Column(String, nullable=True)
    is_abnormal = Column(Boolean, nullable=True)
    abnormal_flag = Column(String, nullable=True)  # H (high), L (low), etc.
    test_date = Column(Date, nullable=True)
    ordering_provider = Column(String, nullable=True)
    lab_facility = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Medical coding
    loinc_code = Column(String, nullable=True)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    document = relationship("Document", back_populates="lab_results")
    user = relationship("User", back_populates="lab_results")

    __table_args__ = (
        Index("idx_lab_document_id", "document_id"),
        Index("idx_lab_user_id", "user_id"),
        Index("idx_lab_test_name", "test_name"),
        Index("idx_lab_is_abnormal", "is_abnormal"),
        Index("idx_lab_test_date", "test_date"),
        Index("idx_lab_deleted_at", "deleted_at"),
        Index("idx_lab_loinc", "loinc_code"),
    )


class ClinicalVitalSign(Base):
    """
    Vital signs extracted from documents.
    Normalized from Agent 2 clinical_data.vital_signs
    """

    __tablename__ = "clinical_vital_signs"

    id = Column(String, primary_key=True)
    document_id = Column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Core fields (from Agent 2 output)
    measurement_date = Column(DateTime, nullable=True)

    # Vital signs
    systolic_bp = Column(Float, nullable=True)
    diastolic_bp = Column(Float, nullable=True)
    heart_rate = Column(Float, nullable=True)
    respiratory_rate = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    temperature_unit = Column(String, nullable=True)  # F or C
    oxygen_saturation = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    weight_unit = Column(String, nullable=True)  # kg or lbs
    height = Column(Float, nullable=True)
    height_unit = Column(String, nullable=True)  # cm or inches
    bmi = Column(Float, nullable=True)

    notes = Column(Text, nullable=True)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    document = relationship("Document", back_populates="vital_signs")
    user = relationship("User", back_populates="vital_signs")

    __table_args__ = (
        Index("idx_vital_document_id", "document_id"),
        Index("idx_vital_user_id", "user_id"),
        Index("idx_vital_measurement_date", "measurement_date"),
        Index("idx_vital_deleted_at", "deleted_at"),
    )


class ClinicalProcedure(Base):
    """
    Medical procedures extracted from documents.
    Normalized from Agent 2 clinical_data.procedures
    """

    __tablename__ = "clinical_procedures"

    id = Column(String, primary_key=True)
    document_id = Column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Core fields (from Agent 2 output)
    procedure_name = Column(String, nullable=False)
    performed_date = Column(Date, nullable=True)
    provider = Column(String, nullable=True)
    facility = Column(String, nullable=True)
    body_site = Column(String, nullable=True)
    indication = Column(String, nullable=True)  # Why it was done
    outcome = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Medical coding
    cpt_code = Column(String, nullable=True)
    icd10_pcs_code = Column(String, nullable=True)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    document = relationship("Document", back_populates="procedures")
    user = relationship("User", back_populates="procedures")

    __table_args__ = (
        Index("idx_procedure_document_id", "document_id"),
        Index("idx_procedure_user_id", "user_id"),
        Index("idx_procedure_performed_date", "performed_date"),
        Index("idx_procedure_deleted_at", "deleted_at"),
        Index("idx_procedure_cpt", "cpt_code"),
    )


class ClinicalImmunization(Base):
    """
    Immunization records extracted from documents.
    Normalized from Agent 2 clinical_data.immunizations
    """

    __tablename__ = "clinical_immunizations"

    id = Column(String, primary_key=True)
    document_id = Column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Core fields (from Agent 2 output)
    vaccine_name = Column(String, nullable=False)
    administration_date = Column(Date, nullable=True)
    dose_number = Column(Integer, nullable=True)
    site = Column(String, nullable=True)  # Body site of administration
    route = Column(String, nullable=True)  # IM, oral, etc.
    lot_number = Column(String, nullable=True)
    expiration_date = Column(Date, nullable=True)
    manufacturer = Column(String, nullable=True)
    administered_by = Column(String, nullable=True)
    facility = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Medical coding
    cvx_code = Column(String, nullable=True)  # CDC vaccine codes

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    document = relationship("Document", back_populates="immunizations")
    user = relationship("User", back_populates="immunizations")

    __table_args__ = (
        Index("idx_immunization_document_id", "document_id"),
        Index("idx_immunization_user_id", "user_id"),
        Index("idx_immunization_admin_date", "administration_date"),
        Index("idx_immunization_vaccine", "vaccine_name"),
        Index("idx_immunization_deleted_at", "deleted_at"),
    )
