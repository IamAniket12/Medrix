"""Medical ID API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ...core.dependencies import get_db, get_settings
from ...services.medical_id_service import MedicalIDService
from ...services.storage_service import StorageService
from ...models import TemporaryMedicalSummary

router = APIRouter(prefix="/medical-id", tags=["medical-id"])


# Pydantic models for request/response
class GenerateCardRequest(BaseModel):
    """Request to generate permanent card."""

    force_regenerate: bool = False


class GenerateSummaryRequest(BaseModel):
    """Request to generate temporary summary."""

    expiration_minutes: int = 5  # Default 5 minutes


class CardResponse(BaseModel):
    """Permanent card response with patient data."""

    id: str
    card_pdf_path: str
    qr_code_data: str
    version: int
    generated_at: str
    # Patient data fields
    patient_name: str
    date_of_birth: Optional[str] = None
    blood_type: Optional[str] = None
    gender: Optional[str] = None
    emergency_contact: Optional[Dict[str, Optional[str]]] = None
    chronic_conditions: List[Dict[str, Any]] = Field(default_factory=list)
    life_threatening_allergies: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        from_attributes = True


class SummaryResponse(BaseModel):
    """Temporary summary response."""

    id: str
    file_path: str
    pdf_url: str
    expires_at: str
    generated_at: str

    class Config:
        from_attributes = True


class SummaryListItem(BaseModel):
    """Summary list item."""

    id: str
    access_token: str
    expires_at: str
    max_uses: int
    current_uses: int
    is_revoked: bool
    is_expired: bool
    generated_at: str

    class Config:
        from_attributes = True


class AccessResponse(BaseModel):
    """Access verification response."""

    success: bool
    signed_url: str = None
    error: str = None


class EmergencyInfoResponse(BaseModel):
    """Public emergency information response (filtered by MedGemma)."""

    patient_name: str
    age: Optional[int] = None
    blood_type: Optional[str] = None
    gender: Optional[str] = None
    emergency_contact: Optional[Dict[str, Optional[str]]] = None
    critical_conditions: List[str] = Field(default_factory=list)
    life_threatening_allergies: List[str] = Field(default_factory=list)
    emergency_notes: Optional[str] = None  # AI-generated emergency guidance
    last_updated: str

    class Config:
        from_attributes = True


# Helper to get Medical ID service
def get_medical_id_service(settings=Depends(get_settings)) -> MedicalIDService:
    """Get Medical ID service instance."""
    storage_service = StorageService(settings)
    return MedicalIDService(settings, storage_service)


@router.get("/{user_id}/card", response_model=CardResponse)
async def get_permanent_card(
    user_id: str,
    db: Session = Depends(get_db),
    medical_id_service: MedicalIDService = Depends(get_medical_id_service),
):
    """
    Get existing permanent medical ID card or generate if missing.

    Args:
        user_id: User ID

    Returns:
        Permanent card info with PDF path and QR code
    """
    try:
        card = await medical_id_service.generate_permanent_card(
            db, user_id, force_regenerate=False
        )
        # Convert datetime to ISO string
        card["generated_at"] = card["generated_at"].isoformat()
        return CardResponse(**card)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate permanent card: {str(e)}",
        )


@router.post("/{user_id}/card/regenerate", response_model=CardResponse)
async def regenerate_permanent_card(
    user_id: str,
    db: Session = Depends(get_db),
    medical_id_service: MedicalIDService = Depends(get_medical_id_service),
):
    """
    Force regenerate permanent medical ID card (increment version).

    Args:
        user_id: User ID

    Returns:
        New permanent card info
    """
    try:
        card = await medical_id_service.generate_permanent_card(
            db, user_id, force_regenerate=True
        )
        # Convert datetime to ISO string
        card["generated_at"] = card["generated_at"].isoformat()
        return CardResponse(**card)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate permanent card: {str(e)}",
        )


@router.post("/{user_id}/summary", response_model=SummaryResponse)
async def generate_temporary_summary(
    user_id: str,
    request: GenerateSummaryRequest = GenerateSummaryRequest(),
    db: Session = Depends(get_db),
    medical_id_service: MedicalIDService = Depends(get_medical_id_service),
):
    """
    Generate temporary medical summary with time-limited access.

    Args:
        user_id: User ID
        request: Generation request with expiration minutes

    Returns:
        Temporary summary with access token and QR code
    """
    try:
        summary = await medical_id_service.generate_temporary_summary(
            db, user_id, expiration_minutes=request.expiration_minutes
        )
        return SummaryResponse(**summary)
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate temporary summary: {str(e)}",
        )


@router.get("/{user_id}/summaries", response_model=List[SummaryListItem])
async def list_temporary_summaries(
    user_id: str,
    db: Session = Depends(get_db),
):
    """
    List all temporary summaries for a user (active and expired).

    Args:
        user_id: User ID

    Returns:
        List of temporary summaries
    """
    try:
        from datetime import datetime

        summaries = (
            db.query(TemporaryMedicalSummary)
            .filter(TemporaryMedicalSummary.user_id == user_id)
            .order_by(TemporaryMedicalSummary.created_at.desc())
            .all()
        )

        now = datetime.utcnow()
        result = []
        for summary in summaries:
            result.append(
                SummaryListItem(
                    id=summary.id,
                    access_token=summary.access_token,
                    expires_at=summary.expires_at.isoformat(),
                    max_uses=summary.max_uses,
                    current_uses=summary.current_uses,
                    is_revoked=summary.is_revoked,
                    is_expired=now > summary.expires_at,
                    generated_at=summary.created_at.isoformat(),
                )
            )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list summaries: {str(e)}",
        )


@router.post("/{user_id}/summary/{summary_id}/revoke")
async def revoke_temporary_summary(
    user_id: str,
    summary_id: str,
    db: Session = Depends(get_db),
    medical_id_service: MedicalIDService = Depends(get_medical_id_service),
):
    """
    Revoke a temporary summary (user action).

    Args:
        user_id: User ID (for ownership verification)
        summary_id: Summary ID to revoke

    Returns:
        Success status
    """
    try:
        success = await medical_id_service.revoke_temporary_summary(
            db, summary_id, user_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Summary not found or access denied",
            )

        return {"success": True, "message": "Summary revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke summary: {str(e)}",
        )


@router.get("/access/{access_token}", response_model=AccessResponse)
async def verify_temporary_access(
    access_token: str,
    db: Session = Depends(get_db),
    medical_id_service: MedicalIDService = Depends(get_medical_id_service),
):
    """
    PUBLIC ENDPOINT: Verify temporary access token and return signed URL.

    This endpoint is accessed by healthcare providers via QR code.
    No authentication required but token is time-limited and usage-limited.

    Args:
        access_token: Access token from QR code

    Returns:
        Signed URL if valid, error message otherwise
    """
    try:
        signed_url = await medical_id_service.verify_temporary_access(db, access_token)

        if not signed_url:
            return AccessResponse(
                success=False,
                error="Access denied: Invalid, expired, revoked, or usage limit exceeded",
            )

        return AccessResponse(success=True, signed_url=signed_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify access: {str(e)}",
        )


@router.get("/{user_id}/qr-code")
async def generate_qr_code(
    user_id: str,
    data: str = None,
    medical_id_service: MedicalIDService = Depends(get_medical_id_service),
):
    """
    Generate QR code image for given data or default to permanent card access URL.

    Args:
        user_id: User ID
        data: Optional custom data to encode (defaults to permanent card URL)

    Returns:
        QR code PNG image
    """
    try:
        from fastapi.responses import Response

        if not data:
            # Default to permanent card access URL
            settings = get_settings()
            base_url = getattr(settings, "frontend_url", "https://medrix.app")
            data = f"{base_url}/medical-id/view/{user_id}"

        qr_bytes = medical_id_service.generate_qr_code(data, size=400)

        return Response(content=qr_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate QR code: {str(e)}",
        )


@router.get("/{user_id}/emergency-info", response_model=EmergencyInfoResponse)
async def get_emergency_info(
    user_id: str,
    db: Session = Depends(get_db),
    medical_id_service: MedicalIDService = Depends(get_medical_id_service),
):
    """
    Get public emergency information for a user (filtered by AI).
    This endpoint is publicly accessible via QR code scan.

    Uses MedGemma to:
    - Extract only emergency-critical information
    - Filter out sensitive personal data
    - Format data for first responders

    Args:
        user_id: User ID

    Returns:
        Emergency-safe medical information
    """
    try:
        emergency_info = await medical_id_service.get_emergency_info(db, user_id)
        return EmergencyInfoResponse(**emergency_info)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve emergency info: {str(e)}",
        )
