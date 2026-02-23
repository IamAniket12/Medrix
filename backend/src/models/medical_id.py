"""Medical ID models for permanent cards and temporary summaries."""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class MedicalIDCard(Base, TimestampMixin):
    """Permanent medical ID card for emergency access."""

    __tablename__ = "medical_id_cards"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    card_pdf_path = Column(String, nullable=False)  # GCS path
    qr_code_data = Column(String, nullable=False)  # QR payload for access
    version = Column(Integer, default=1)  # Increment on regeneration

    # Relationship
    user = relationship("User", back_populates="medical_id_cards")


class TemporaryMedicalSummary(Base, TimestampMixin):
    """Temporary medical history summary with time-limited access."""

    __tablename__ = "temporary_medical_summaries"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    access_token = Column(String, unique=True, nullable=False, index=True)
    summary_pdf_path = Column(String, nullable=False)  # GCS path
    expires_at = Column(DateTime, nullable=False, index=True)
    max_uses = Column(Integer, default=5)
    current_uses = Column(Integer, default=0)
    is_revoked = Column(Boolean, default=False, index=True)

    # Relationship
    user = relationship("User", back_populates="temporary_medical_summaries")
