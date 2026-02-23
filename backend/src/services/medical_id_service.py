"""Medical ID Service for generating permanent cards and temporary summaries."""

import io
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
    Image as RLImage,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import qrcode

from ..models import User, MedicalIDCard, TemporaryMedicalSummary
from .storage_service import StorageService
from .medical_id_agent_orchestrator import MedicalIDAgentOrchestrator


class MedicalIDService:
    """Service for generating Medical ID cards and temporary summaries."""

    def __init__(self, settings, storage_service: StorageService):
        """
        Initialize the Medical ID service.

        Args:
            settings: Application settings
            storage_service: Storage service for file uploads
        """
        self.settings = settings
        self.storage_service = storage_service
        self.agent_orchestrator = MedicalIDAgentOrchestrator(settings)

        # Card dimensions (credit card size: 3.375" x 2.125")
        self.CARD_WIDTH = 3.375 * inch
        self.CARD_HEIGHT = 2.125 * inch

    async def generate_permanent_card(
        self, db: Session, user_id: str, force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate or retrieve permanent medical ID card.

        Args:
            db: Database session
            user_id: User ID
            force_regenerate: If True, regenerate even if card exists

        Returns:
            Dict with card info including PDF path, QR code data, and patient data
        """
        # Check if card already exists
        existing_card = (
            db.query(MedicalIDCard)
            .filter(MedicalIDCard.user_id == user_id)
            .order_by(MedicalIDCard.version.desc())
            .first()
        )

        # If existing card and not regenerating, fetch patient data and return
        if existing_card and not force_regenerate:
            print(f"✓ Existing permanent card found (v{existing_card.version})")
            # Fetch current patient data for display
            permanent_data = await self.agent_orchestrator.generate_permanent_id_data(
                db, user_id
            )
            return {
                "id": existing_card.id,
                "card_pdf_path": existing_card.card_pdf_path,
                "qr_code_data": existing_card.qr_code_data,
                "version": existing_card.version,
                "generated_at": existing_card.created_at,
                "patient_name": permanent_data.patient_name,
                "date_of_birth": permanent_data.date_of_birth,
                "blood_type": permanent_data.blood_type,
                "gender": permanent_data.gender,
                "emergency_contact": (
                    permanent_data.emergency_contact.model_dump()
                    if permanent_data.emergency_contact
                    else None
                ),
                "chronic_conditions": [
                    cond.model_dump() for cond in permanent_data.chronic_conditions
                ],
                "life_threatening_allergies": [
                    allergy.model_dump()
                    for allergy in permanent_data.life_threatening_allergies
                ],
            }

        # Use agent to retrieve critical data
        print(f"🔍 Generating permanent card for user {user_id}")
        permanent_data = await self.agent_orchestrator.generate_permanent_id_data(
            db, user_id
        )

        # Generate QR code data (link to access portal)
        base_url = getattr(self.settings, "frontend_url", "https://medrix.app")
        qr_code_data = f"{base_url}/medical-id/view/{user_id}"

        # Generate PDF
        try:
            pdf_bytes = self._generate_permanent_card_pdf(
                permanent_data, qr_code_data, user_id
            )
            print(f"✓ PDF generated successfully ({len(pdf_bytes)} bytes)")
        except Exception as pdf_error:
            print(f"❌ PDF generation failed: {pdf_error}")
            import traceback

            traceback.print_exc()
            raise

        # Upload to GCS
        try:
            version = (existing_card.version + 1) if existing_card else 1
            upload_result = await self.storage_service.save_file(
                file_content=io.BytesIO(pdf_bytes),
                original_filename=f"{user_id}_medical_id_v{version}.pdf",
                folder="medical-id/permanent",
            )
            gcs_path = upload_result["file_path"]
            print(f"✓ Uploaded to GCS: {gcs_path}")
        except Exception as upload_error:
            print(f"❌ GCS upload failed: {upload_error}")
            import traceback

            traceback.print_exc()
            raise

        # Create database record
        card_id = str(uuid.uuid4())
        new_card = MedicalIDCard(
            id=card_id,
            user_id=user_id,
            card_pdf_path=gcs_path,
            qr_code_data=qr_code_data,
            version=version,
        )

        db.add(new_card)
        db.commit()
        db.refresh(new_card)

        print(f"✓ Permanent card generated (v{version}): {gcs_path}")

        return {
            "id": new_card.id,
            "card_pdf_path": new_card.card_pdf_path,
            "qr_code_data": new_card.qr_code_data,
            "version": new_card.version,
            "generated_at": new_card.created_at,
            "patient_name": permanent_data.patient_name,
            "date_of_birth": permanent_data.date_of_birth,
            "blood_type": permanent_data.blood_type,
            "gender": permanent_data.gender,
            "emergency_contact": (
                permanent_data.emergency_contact.model_dump()
                if permanent_data.emergency_contact
                else None
            ),
            "chronic_conditions": [
                cond.model_dump() for cond in permanent_data.chronic_conditions
            ],
            "life_threatening_allergies": [
                allergy.model_dump()
                for allergy in permanent_data.life_threatening_allergies
            ],
        }

    async def get_emergency_info(self, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Get public emergency information filtered by MedGemma AI.
        This data is safe to display publicly via QR code.

        Uses MedGemma to:
        - Extract only emergency-critical information
        - Filter out sensitive personal details
        - Format for first responders/emergency personnel

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Dict with emergency-safe medical information
        """
        from ..models import User

        print(f"🚨 Fetching emergency info for user {user_id}")

        # Get permanent ID data (already filtered by agent)
        permanent_data = await self.agent_orchestrator.generate_permanent_id_data(
            db, user_id
        )

        # Get user for age calculation
        user = db.query(User).filter(User.id == user_id).first()
        age = None
        if user and user.date_of_birth:
            from datetime import datetime

            try:
                dob = datetime.fromisoformat(str(user.date_of_birth))
                today = datetime.utcnow()
                age = (
                    today.year
                    - dob.year
                    - ((today.month, today.day) < (dob.month, dob.day))
                )
            except Exception:
                age = None

        # Use MedGemma to generate emergency-appropriate notes
        emergency_prompt = f"""You are an emergency medical AI assistant. Generate brief, critical guidance for first responders based on this patient data.

Patient: {permanent_data.patient_name}
Age: {age if age else 'Unknown'}
Blood Type: {permanent_data.blood_type or 'Unknown'}
Gender: {permanent_data.gender or 'Unknown'}

Critical Conditions: {', '.join([c.name for c in permanent_data.chronic_conditions]) if permanent_data.chronic_conditions else 'None documented'}

Life-Threatening Allergies: {', '.join([a.allergen for a in permanent_data.life_threatening_allergies]) if permanent_data.life_threatening_allergies else 'None documented'}

Emergency Contact: {permanent_data.emergency_contact.name if permanent_data.emergency_contact else 'Not available'} {permanent_data.emergency_contact.phone if permanent_data.emergency_contact and permanent_data.emergency_contact.phone else ''}

Generate a 2-3 sentence emergency guidance note for first responders. Focus ONLY on:
- Immediate treatment considerations
- Drug/allergy warnings  
- Critical monitoring needs

Respond ONLY with plain text (no JSON, no markdown, no code blocks). Start directly with the guidance text."""

        # Call MedGemma for emergency notes
        emergency_notes = None
        try:
            emergency_notes = await self.agent_orchestrator._call_llm_text_only(
                emergency_prompt, output_format="text"
            )
            # Clean up the response
            if emergency_notes:
                emergency_notes = emergency_notes.strip()

                # Remove any markdown formatting that might slip through
                import re

                # Remove markdown bold
                emergency_notes = re.sub(r"\*\*([^*]+)\*\*", r"\1", emergency_notes)
                # Remove markdown italic
                emergency_notes = re.sub(r"\*([^*]+)\*", r"\1", emergency_notes)
                # Remove markdown headers
                emergency_notes = re.sub(
                    r"^#+\s+", "", emergency_notes, flags=re.MULTILINE
                )

                # Limit to 500 characters for safety
                if len(emergency_notes) > 500:
                    emergency_notes = emergency_notes[:497] + "..."
        except Exception as e:
            print(f"⚠️ MedGemma emergency notes failed: {e}")
            emergency_notes = (
                "Standard emergency protocols apply. Monitor vital signs closely."
            )

        return {
            "patient_name": permanent_data.patient_name,
            "age": age,
            "blood_type": permanent_data.blood_type,
            "gender": permanent_data.gender,
            "emergency_contact": (
                permanent_data.emergency_contact.model_dump()
                if permanent_data.emergency_contact
                else None
            ),
            "critical_conditions": [
                cond.name for cond in permanent_data.chronic_conditions
            ],
            "life_threatening_allergies": [
                allergy.allergen
                for allergy in permanent_data.life_threatening_allergies
            ],
            "emergency_notes": emergency_notes,
            "last_updated": permanent_data.last_updated,
        }

    async def generate_temporary_summary(
        self, db: Session, user_id: str, expiration_minutes: int = 5
    ) -> Dict[str, Any]:
        """
        Generate temporary medical summary - simple version.

        Args:
            db: Database session
            user_id: User ID
            expiration_minutes: Minutes until summary expires (default 5)

        Returns:
            Dict with summary info including PDF path
        """
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(minutes=expiration_minutes)

        # Use agent to retrieve comprehensive data
        print(f"🔍 Generating temporary summary for user {user_id}")
        try:
            summary_data = (
                await self.agent_orchestrator.generate_temporary_summary_data(
                    db, user_id, expires_at
                )
            )
            print(f"✓ Agent returned summary_data type: {type(summary_data)}")
            print(f"  patient_name: {summary_data.patient_name}")
            print(f"  medications: {len(summary_data.all_medications)}")
            print(f"  vitals: {len(summary_data.all_vitals)}")
            print(f"  labs: {len(summary_data.all_lab_results)}")
            print(
                f"  vital types: {[type(v).__name__ for v in summary_data.all_vitals]}"
            )
        except Exception as agent_error:
            print(f"❌ Agent/data conversion error: {agent_error}")
            import traceback

            traceback.print_exc()
            raise

        # Generate PDF
        print(f"📄 Generating PDF...")
        try:
            pdf_bytes = self._generate_temporary_summary_pdf(
                summary_data, "", expires_at  # Empty QR code data for now
            )
            print(f"✓ PDF generated ({len(pdf_bytes)} bytes)")
        except Exception as pdf_err:
            print(f"❌ PDF generation error: {pdf_err}")
            import traceback

            traceback.print_exc()
            raise

        # Save to uploads folder (simple approach)
        import os

        uploads_dir = os.path.join(os.getcwd(), "uploads", "temp-summaries")
        os.makedirs(uploads_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{user_id}_{timestamp}.pdf"
        file_path = os.path.join(uploads_dir, filename)

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        print(f"✓ PDF saved to {file_path}")

        # For now, return simple response without database record
        return {
            "id": str(uuid.uuid4()),
            "file_path": f"/uploads/temp-summaries/{filename}",
            "pdf_url": f"/uploads/temp-summaries/{filename}",
            "expires_at": expires_at.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
        }

        return {
            "id": new_summary.id,
            "access_token": new_summary.access_token,
            "qr_code_data": qr_code_data,
            "summary_pdf_path": new_summary.summary_pdf_path,
            "expires_at": new_summary.expires_at,
            "max_uses": new_summary.max_uses,
            "current_uses": new_summary.current_uses,
            "generated_at": new_summary.created_at,
        }

    async def verify_temporary_access(
        self, db: Session, access_token: str
    ) -> Optional[str]:
        """
        Verify temporary access token and return signed URL if valid.

        Args:
            db: Database session
            access_token: Access token from QR code

        Returns:
            Signed GCS URL if valid, None otherwise
        """
        # Query summary
        summary = (
            db.query(TemporaryMedicalSummary)
            .filter(TemporaryMedicalSummary.access_token == access_token)
            .first()
        )

        if not summary:
            print(f"❌ Access token not found: {access_token}")
            return None

        # Check expiration
        if datetime.utcnow() > summary.expires_at:
            print(f"❌ Access token expired: {access_token}")
            return None

        # Check revocation
        if summary.is_revoked:
            print(f"❌ Access token revoked: {access_token}")
            return None

        # Check usage limit
        if summary.current_uses >= summary.max_uses:
            print(f"❌ Access token usage limit reached: {access_token}")
            return None

        # Increment usage count
        summary.current_uses += 1
        db.commit()

        # Generate signed URL (1 hour expiration)
        signed_url = await self.storage_service.generate_signed_url(
            summary.summary_pdf_path, expiration_hours=1
        )

        print(f"✓ Access granted: {summary.current_uses}/{summary.max_uses} uses")

        return signed_url

    async def revoke_temporary_summary(
        self, db: Session, summary_id: str, user_id: str
    ) -> bool:
        """
        Revoke a temporary summary (user action).

        Args:
            db: Database session
            summary_id: Summary ID to revoke
            user_id: User ID (for ownership verification)

        Returns:
            True if revoked successfully, False otherwise
        """
        summary = (
            db.query(TemporaryMedicalSummary)
            .filter(
                TemporaryMedicalSummary.id == summary_id,
                TemporaryMedicalSummary.user_id == user_id,
            )
            .first()
        )

        if not summary:
            print(f"❌ Summary not found or access denied: {summary_id}")
            return False

        summary.is_revoked = True
        db.commit()

        print(f"✓ Summary revoked: {summary_id}")
        return True

    def _generate_permanent_card_pdf(
        self, permanent_data, qr_code_data: str, user_id: str
    ) -> bytes:
        """
        Generate PDF for permanent medical ID card (official ID style).

        Args:
            permanent_data: PermanentIDData from agent
            qr_code_data: QR code URL
            user_id: User ID for card identification

        Returns:
            PDF bytes
        """
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(self.CARD_WIDTH, self.CARD_HEIGHT))

        # Card dimensions
        width = self.CARD_WIDTH
        height = self.CARD_HEIGHT
        margin = 0.15 * inch

        # Header banner (top of card)
        c.setFillColor(colors.HexColor("#1565C0"))
        c.rect(0, height - 0.5 * inch, width, 0.5 * inch, fill=True, stroke=False)

        # Title in header
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width / 2, height - 0.35 * inch, "MEDICAL EMERGENCY ID")

        # Generate QR code and embed it
        try:
            qr_bytes = self.generate_qr_code(qr_code_data, size=100)
            qr_image = ImageReader(io.BytesIO(qr_bytes))

            # Position QR code (top right)
            qr_x = width - 0.9 * inch
            qr_y = height - 1.45 * inch
            qr_size = 0.8 * inch
            c.drawImage(qr_image, qr_x, qr_y, width=qr_size, height=qr_size)
        except Exception as qr_error:
            print(f"⚠️ QR code generation failed: {qr_error}")
            # Continue without QR code

        # Photo placeholder (left side)
        photo_x = margin
        photo_y = height - 1.5 * inch
        photo_width = 0.9 * inch
        photo_height = 1.1 * inch

        c.setFillColor(colors.HexColor("#E0E0E0"))
        c.rect(photo_x, photo_y, photo_width, photo_height, fill=True, stroke=True)
        c.setFillColor(colors.grey)
        c.setFont("Helvetica", 7)
        c.drawCentredString(
            photo_x + photo_width / 2, photo_y + photo_height / 2, "PHOTO"
        )

        # Patient Information Section (right of photo)
        info_x = photo_x + photo_width + 0.15 * inch
        info_y = height - 0.8 * inch

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(info_x, info_y, "NAME:")
        c.setFont("Helvetica", 9)
        patient_name = permanent_data.patient_name or "Unknown"
        c.drawString(info_x + 0.5 * inch, info_y, patient_name[:25])

        # Demographics in a structured format
        info_y -= 0.2 * inch
        c.setFont("Helvetica-Bold", 8)
        c.drawString(info_x, info_y, "DOB:")
        c.setFont("Helvetica", 8)
        dob = permanent_data.date_of_birth or "N/A"
        c.drawString(info_x + 0.5 * inch, info_y, str(dob))

        info_y -= 0.15 * inch
        c.setFont("Helvetica-Bold", 8)
        c.drawString(info_x, info_y, "BLOOD:")
        c.setFont("Helvetica", 8)
        blood_type = permanent_data.blood_type or "Unknown"
        c.drawString(info_x + 0.5 * inch, info_y, blood_type)

        # Add gender if available
        if permanent_data.gender:
            info_y -= 0.15 * inch
            c.setFont("Helvetica-Bold", 8)
            c.drawString(info_x, info_y, "GENDER:")
            c.setFont("Helvetica", 8)
            c.drawString(info_x + 0.5 * inch, info_y, permanent_data.gender[:1])

        # Divider line
        line_y = photo_y - 0.1 * inch
        c.setStrokeColor(colors.HexColor("#BDBDBD"))
        c.setLineWidth(0.5)
        c.line(margin, line_y, width - margin, line_y)

        # Medical Information Section
        med_y = line_y - 0.15 * inch

        # Chronic Conditions
        if permanent_data.chronic_conditions:
            c.setFillColor(colors.HexColor("#D32F2F"))
            c.setFont("Helvetica-Bold", 7)
            c.drawString(margin, med_y, "⚠ CONDITIONS:")
            med_y -= 0.12 * inch

            c.setFillColor(colors.black)
            c.setFont("Helvetica", 6.5)
            for idx, cond in enumerate(permanent_data.chronic_conditions[:3]):
                cond_text = f"• {cond.name}"
                if cond.severity:
                    cond_text += f" ({cond.severity})"
                # Truncate if too long
                if len(cond_text) > 45:
                    cond_text = cond_text[:42] + "..."
                c.drawString(margin + 0.05 * inch, med_y, cond_text)
                med_y -= 0.11 * inch
                if med_y < margin + 0.5 * inch:
                    break

        # Allergies
        if permanent_data.life_threatening_allergies:
            med_y -= 0.05 * inch
            c.setFillColor(colors.HexColor("#F57C00"))
            c.setFont("Helvetica-Bold", 7)
            c.drawString(margin, med_y, "⚠ ALLERGIES:")
            med_y -= 0.12 * inch

            c.setFillColor(colors.black)
            c.setFont("Helvetica", 6.5)
            for idx, allergy in enumerate(
                permanent_data.life_threatening_allergies[:3]
            ):
                allergy_text = f"• {allergy.allergen}"
                if allergy.reaction:
                    allergy_text += f" → {allergy.reaction}"
                if len(allergy_text) > 45:
                    allergy_text = allergy_text[:42] + "..."
                c.drawString(margin + 0.05 * inch, med_y, allergy_text)
                med_y -= 0.11 * inch
                if med_y < margin + 0.3 * inch:
                    break

        # Emergency Contact (bottom)
        if permanent_data.emergency_contact:
            ec = permanent_data.emergency_contact
            if ec.name or ec.phone:
                footer_y = margin + 0.1 * inch
                c.setFillColor(colors.HexColor("#424242"))
                c.setFont("Helvetica-Bold", 6)
                c.drawString(margin, footer_y, "EMERGENCY:")
                c.setFont("Helvetica", 6)
                ec_text = ""
                if ec.name:
                    ec_text += ec.name[:20]
                if ec.phone:
                    ec_text += f"  {ec.phone}"
                c.drawString(margin + 0.5 * inch, footer_y, ec_text)

        # Card ID number (bottom right)
        c.setFont("Helvetica", 5)
        c.setFillColor(colors.grey)
        c.drawRightString(width - margin, margin + 0.05 * inch, f"ID: {user_id[:12]}")

        # Save PDF
        c.save()

        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    def _generate_temporary_summary_pdf(
        self, summary_data, qr_code_data: str, expires_at: datetime
    ) -> bytes:
        """
        Generate a professionally designed PDF for temporary medical summary.

        Args:
            summary_data: TemporarySummaryData from agent
            qr_code_data: QR code URL (not used in simple version)
            expires_at: Expiration datetime

        Returns:
            PDF bytes
        """
        # ── Colour palette ────────────────────────────────────────────────
        C_NAVY = colors.HexColor("#1E3A5F")
        C_ORANGE = colors.HexColor("#F97316")
        C_ORANGE_LT = colors.HexColor("#FFF7ED")
        C_SECTION_BG = colors.HexColor("#EEF2FF")
        C_ROW_ALT = colors.HexColor("#F8FAFF")
        C_RED = colors.HexColor("#DC2626")
        C_RED_LT = colors.HexColor("#FEF2F2")
        C_GREEN = colors.HexColor("#16A34A")
        C_AMBER = colors.HexColor("#D97706")
        C_AMBER_LT = colors.HexColor("#FFFBEB")
        C_GREY_TEXT = colors.HexColor("#6B7280")
        C_BORDER = colors.HexColor("#D1D5DB")
        C_WHITE = colors.white

        # ── Helper: section header strip ─────────────────────────────────
        def section_header(label, icon=""):
            full_label = f"{icon}  {label}" if icon else label
            hdr_para = Paragraph(
                full_label,
                ParagraphStyle(
                    "SectionHdr",
                    parent=styles["Normal"],
                    fontSize=10,
                    fontName="Helvetica-Bold",
                    textColor=C_NAVY,
                    leftIndent=4,
                ),
            )
            tbl = Table([[hdr_para]], colWidths=[6.5 * inch])
            tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), C_SECTION_BG),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("LINEBELOW", (0, 0), (-1, -1), 1.5, C_ORANGE),
                    ]
                )
            )
            return tbl

        # ── Helper: empty-state paragraph ────────────────────────────────
        def empty_note(text):
            return Paragraph(
                f"<i>{text}</i>",
                ParagraphStyle(
                    "EmptyNote",
                    parent=styles["Normal"],
                    fontSize=9,
                    textColor=C_GREY_TEXT,
                    leftIndent=8,
                ),
            )

        # ── Helper: body paragraph ────────────────────────────────────────
        def body_para(markup, indent=8):
            return Paragraph(
                markup,
                ParagraphStyle(
                    "Body",
                    parent=styles["Normal"],
                    fontSize=9,
                    leftIndent=indent,
                    spaceAfter=2,
                ),
            )

        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                leftMargin=0.75 * inch,
                rightMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch,
            )

            styles = getSampleStyleSheet()
            story = []

            # ── BRANDED HEADER ────────────────────────────────────────────
            patient_name = str(summary_data.patient_name or "Patient")
            header_rows = [
                [
                    Paragraph(
                        "MEDRIX",
                        ParagraphStyle(
                            "Brand",
                            parent=styles["Normal"],
                            fontSize=13,
                            fontName="Helvetica-Bold",
                            textColor=C_ORANGE,
                        ),
                    ),
                    Paragraph(
                        f"Generated: {datetime.utcnow().strftime('%d %b %Y, %H:%M')} UTC",
                        ParagraphStyle(
                            "GenDate",
                            parent=styles["Normal"],
                            fontSize=8,
                            textColor=C_WHITE,
                            alignment=TA_RIGHT,
                        ),
                    ),
                ],
                [
                    Paragraph(
                        "Medical Summary for Your Doctor",
                        ParagraphStyle(
                            "DocTitle",
                            parent=styles["Normal"],
                            fontSize=18,
                            fontName="Helvetica-Bold",
                            textColor=C_WHITE,
                            spaceAfter=0,
                        ),
                    ),
                    Paragraph(
                        patient_name,
                        ParagraphStyle(
                            "PatientNameHdr",
                            parent=styles["Normal"],
                            fontSize=14,
                            fontName="Helvetica-Bold",
                            textColor=C_ORANGE,
                            alignment=TA_RIGHT,
                        ),
                    ),
                ],
            ]
            header_tbl = Table(header_rows, colWidths=[4.0 * inch, 2.5 * inch])
            header_tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), C_NAVY),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ("LEFTPADDING", (0, 0), (-1, -1), 14),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                        ("SPAN", (0, 0), (0, 0)),
                    ]
                )
            )
            story.append(header_tbl)

            # ── EXPIRATION BANNER ─────────────────────────────────────────
            exp_para = Paragraph(
                f"  This document expires on {expires_at.strftime('%d %b %Y at %H:%M UTC')}. "
                f"Do not use after this date.",
                ParagraphStyle(
                    "ExpBanner",
                    parent=styles["Normal"],
                    fontSize=8,
                    fontName="Helvetica-Bold",
                    textColor=C_AMBER,
                ),
            )
            exp_tbl = Table([[exp_para]], colWidths=[6.5 * inch])
            exp_tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), C_AMBER_LT),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("BOX", (0, 0), (-1, -1), 0.75, C_AMBER),
                    ]
                )
            )
            story.append(exp_tbl)
            story.append(Spacer(1, 0.18 * inch))

            # ── AI CLINICAL BRIEFING ──────────────────────────────────────
            ai = getattr(summary_data, "clinical_ai_summary", None)
            if ai:
                risk_colors_map = {
                    "critical": "#B91C1C",
                    "high": "#DC2626",
                    "moderate": "#D97706",
                    "low": "#16A34A",
                    "unknown": "#6B7280",
                }
                risk = (ai.risk_level or "unknown").lower()
                risk_hex = risk_colors_map.get(risk, "#6B7280")
                risk_color = colors.HexColor(risk_hex)
                confidence = (ai.ai_confidence or "moderate").capitalize()

                # Header bar
                ai_hdr_para = Paragraph(
                    f"AI CLINICAL BRIEFING  |  RISK: {risk.upper()}  |  Confidence: {confidence}",
                    ParagraphStyle(
                        "AIHdr",
                        parent=styles["Normal"],
                        fontSize=10,
                        fontName="Helvetica-Bold",
                        textColor=C_WHITE,
                    ),
                )
                ai_hdr_tbl = Table([[ai_hdr_para]], colWidths=[6.5 * inch])
                ai_hdr_tbl.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), risk_color),
                            ("TOPPADDING", (0, 0), (-1, -1), 8),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                            ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ]
                    )
                )
                story.append(ai_hdr_tbl)

                ai_body_style = ParagraphStyle(
                    "AIBody", parent=styles["Normal"], fontSize=9, spaceAfter=4
                )
                ai_body_items = []

                if ai.clinical_overview:
                    ai_body_items.append(
                        Paragraph(
                            f"<b>Overview:</b> {ai.clinical_overview}", ai_body_style
                        )
                    )
                if ai.active_concerns:
                    concerns_html = "<b>Active Concerns:</b><br/>" + "<br/>".join(
                        f"&nbsp;&nbsp;• {c}" for c in ai.active_concerns
                    )
                    ai_body_items.append(Paragraph(concerns_html, ai_body_style))
                if ai.medication_review:
                    ai_body_items.append(
                        Paragraph(
                            f"<b>Medication Review:</b> {ai.medication_review}",
                            ai_body_style,
                        )
                    )
                if ai.lab_flags:
                    ai_body_items.append(
                        Paragraph(f"<b>Lab Flags:</b> {ai.lab_flags}", ai_body_style)
                    )
                if ai.vital_trend:
                    ai_body_items.append(
                        Paragraph(
                            f"<b>Vital Trend:</b> {ai.vital_trend}", ai_body_style
                        )
                    )
                if ai.recommended_actions:
                    actions_html = "<b>Recommended Actions:</b><br/>" + "<br/>".join(
                        f"&nbsp;&nbsp;• {a}" for a in ai.recommended_actions
                    )
                    ai_body_items.append(Paragraph(actions_html, ai_body_style))

                if ai_body_items:
                    ai_body_rows = [[item] for item in ai_body_items]
                    ai_body_tbl = Table(ai_body_rows, colWidths=[6.5 * inch])
                    ai_body_tbl.setStyle(
                        TableStyle(
                            [
                                (
                                    "BACKGROUND",
                                    (0, 0),
                                    (-1, -1),
                                    colors.HexColor("#EFF6FF"),
                                ),
                                ("TOPPADDING", (0, 0), (-1, -1), 6),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                                ("BOX", (0, 0), (-1, -1), 0.75, risk_color),
                                ("LINEBELOW", (0, 0), (-1, -2), 0.3, C_BORDER),
                            ]
                        )
                    )
                    story.append(ai_body_tbl)

                story.append(Spacer(1, 0.2 * inch))

            # ── PATIENT INFORMATION ───────────────────────────────────────
            story.append(section_header("PATIENT INFORMATION", ""))
            story.append(Spacer(1, 0.05 * inch))

            dob_str = str(summary_data.date_of_birth or "—")
            blood_str = str(summary_data.blood_type or "—")
            gender_str = str(summary_data.gender or "—")
            phone_str = str(summary_data.phone or "—")

            pt_rows = [
                [
                    Paragraph(
                        "<b>Name</b>",
                        ParagraphStyle(
                            "PL",
                            parent=styles["Normal"],
                            fontSize=9,
                            fontName="Helvetica-Bold",
                        ),
                    ),
                    Paragraph(
                        patient_name,
                        ParagraphStyle("PV", parent=styles["Normal"], fontSize=9),
                    ),
                    Paragraph(
                        "<b>Date of Birth</b>",
                        ParagraphStyle(
                            "PL",
                            parent=styles["Normal"],
                            fontSize=9,
                            fontName="Helvetica-Bold",
                        ),
                    ),
                    Paragraph(
                        dob_str,
                        ParagraphStyle("PV", parent=styles["Normal"], fontSize=9),
                    ),
                ],
                [
                    Paragraph(
                        "<b>Blood Type</b>",
                        ParagraphStyle(
                            "PL",
                            parent=styles["Normal"],
                            fontSize=9,
                            fontName="Helvetica-Bold",
                        ),
                    ),
                    Paragraph(
                        blood_str,
                        ParagraphStyle("PV", parent=styles["Normal"], fontSize=9),
                    ),
                    Paragraph(
                        "<b>Gender</b>",
                        ParagraphStyle(
                            "PL",
                            parent=styles["Normal"],
                            fontSize=9,
                            fontName="Helvetica-Bold",
                        ),
                    ),
                    Paragraph(
                        gender_str,
                        ParagraphStyle("PV", parent=styles["Normal"], fontSize=9),
                    ),
                ],
                [
                    Paragraph(
                        "<b>Phone</b>",
                        ParagraphStyle(
                            "PL",
                            parent=styles["Normal"],
                            fontSize=9,
                            fontName="Helvetica-Bold",
                        ),
                    ),
                    Paragraph(
                        phone_str,
                        ParagraphStyle("PV", parent=styles["Normal"], fontSize=9),
                    ),
                    Paragraph("", styles["Normal"]),
                    Paragraph("", styles["Normal"]),
                ],
            ]
            pt_tbl = Table(
                pt_rows, colWidths=[1.3 * inch, 2.0 * inch, 1.3 * inch, 1.9 * inch]
            )
            pt_tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, -1), C_ROW_ALT),
                        ("BACKGROUND", (2, 0), (2, -1), C_ROW_ALT),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
                    ]
                )
            )
            story.append(pt_tbl)
            story.append(Spacer(1, 0.18 * inch))

            # ── MEDICATIONS ───────────────────────────────────────────────
            story.append(section_header("CURRENT MEDICATIONS", ""))
            story.append(Spacer(1, 0.05 * inch))
            if summary_data.all_medications and len(summary_data.all_medications) > 0:
                active_meds = [
                    m
                    for m in summary_data.all_medications
                    if getattr(m, "is_active", True)
                ]
                inactive_meds = [
                    m
                    for m in summary_data.all_medications
                    if not getattr(m, "is_active", True)
                ]
                for group_label, group, bg in [
                    ("Active", active_meds, C_WHITE),
                    ("Historical", inactive_meds, C_ROW_ALT),
                ]:
                    if not group:
                        continue
                    story.append(
                        Paragraph(
                            f"<b>{group_label}</b>",
                            ParagraphStyle(
                                "GrpLbl",
                                parent=styles["Normal"],
                                fontSize=8,
                                textColor=C_GREY_TEXT,
                                fontName="Helvetica-Bold",
                                leftIndent=6,
                                spaceAfter=2,
                                spaceBefore=4,
                            ),
                        )
                    )
                    med_hdr = [
                        Paragraph(
                            "<b>Medication</b>",
                            ParagraphStyle(
                                "MH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Dose</b>",
                            ParagraphStyle(
                                "MH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Frequency</b>",
                            ParagraphStyle(
                                "MH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Route</b>",
                            ParagraphStyle(
                                "MH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>For</b>",
                            ParagraphStyle(
                                "MH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                    ]
                    med_rows = [med_hdr]
                    for i, med in enumerate(group):
                        try:
                            row_bg = C_ROW_ALT if i % 2 == 1 else C_WHITE
                            med_rows.append(
                                [
                                    Paragraph(
                                        f"<b>{str(med.name)}</b>",
                                        ParagraphStyle(
                                            "MC", parent=styles["Normal"], fontSize=8
                                        ),
                                    ),
                                    Paragraph(
                                        str(getattr(med, "dosage", None) or "—"),
                                        ParagraphStyle(
                                            "MC", parent=styles["Normal"], fontSize=8
                                        ),
                                    ),
                                    Paragraph(
                                        str(getattr(med, "frequency", None) or "—"),
                                        ParagraphStyle(
                                            "MC", parent=styles["Normal"], fontSize=8
                                        ),
                                    ),
                                    Paragraph(
                                        str(getattr(med, "route", None) or "—"),
                                        ParagraphStyle(
                                            "MC", parent=styles["Normal"], fontSize=8
                                        ),
                                    ),
                                    Paragraph(
                                        str(getattr(med, "indication", None) or "—"),
                                        ParagraphStyle(
                                            "MC", parent=styles["Normal"], fontSize=8
                                        ),
                                    ),
                                ]
                            )
                        except Exception as med_err:
                            print(f"⚠️  Med format error: {med_err}")
                    med_tbl = Table(
                        med_rows,
                        colWidths=[
                            1.7 * inch,
                            1.0 * inch,
                            1.2 * inch,
                            0.8 * inch,
                            1.8 * inch,
                        ],
                    )
                    med_style_cmds = [
                        ("BACKGROUND", (0, 0), (-1, 0), C_NAVY),
                        ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
                    ]
                    for i in range(1, len(med_rows)):
                        if i % 2 == 0:
                            med_style_cmds.append(
                                ("BACKGROUND", (0, i), (-1, i), C_ROW_ALT)
                            )
                    med_tbl.setStyle(TableStyle(med_style_cmds))
                    story.append(med_tbl)
                    story.append(Spacer(1, 0.06 * inch))
            else:
                story.append(empty_note("No medications recorded."))
            story.append(Spacer(1, 0.15 * inch))

            # ── MEDICAL CONDITIONS ────────────────────────────────────────
            story.append(section_header("MEDICAL CONDITIONS", ""))
            story.append(Spacer(1, 0.05 * inch))
            if summary_data.all_conditions and len(summary_data.all_conditions) > 0:
                cond_rows = [
                    [
                        Paragraph(
                            "<b>Condition</b>",
                            ParagraphStyle(
                                "CH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Status</b>",
                            ParagraphStyle(
                                "CH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Severity</b>",
                            ParagraphStyle(
                                "CH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                    ]
                ]
                for i, cond in enumerate(summary_data.all_conditions):
                    try:
                        status_val = str(getattr(cond, "status", None) or "—")
                        severity_val = str(getattr(cond, "severity", None) or "—")
                        cond_rows.append(
                            [
                                Paragraph(
                                    f"<b>{str(cond.name)}</b>",
                                    ParagraphStyle(
                                        "CC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    status_val,
                                    ParagraphStyle(
                                        "CC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    severity_val,
                                    ParagraphStyle(
                                        "CC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                            ]
                        )
                    except Exception as ce:
                        print(f"⚠️  Condition format error: {ce}")
                cond_tbl = Table(
                    cond_rows, colWidths=[3.5 * inch, 1.5 * inch, 1.5 * inch]
                )
                cond_style_cmds = [
                    ("BACKGROUND", (0, 0), (-1, 0), C_NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
                ]
                for i in range(1, len(cond_rows)):
                    if i % 2 == 0:
                        cond_style_cmds.append(
                            ("BACKGROUND", (0, i), (-1, i), C_ROW_ALT)
                        )
                cond_tbl.setStyle(TableStyle(cond_style_cmds))
                story.append(cond_tbl)
            else:
                story.append(empty_note("No conditions recorded."))
            story.append(Spacer(1, 0.15 * inch))

            # ── ALLERGIES ─────────────────────────────────────────────────
            story.append(section_header("ALLERGIES & ADVERSE REACTIONS", ""))
            story.append(Spacer(1, 0.05 * inch))
            if summary_data.all_allergies and len(summary_data.all_allergies) > 0:
                allergy_rows = [
                    [
                        Paragraph(
                            "<b>Allergen</b>",
                            ParagraphStyle(
                                "AH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Severity</b>",
                            ParagraphStyle(
                                "AH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Reaction</b>",
                            ParagraphStyle(
                                "AH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                    ]
                ]
                allergy_style_cmds = [
                    ("BACKGROUND", (0, 0), (-1, 0), C_NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
                ]
                for i, allergy in enumerate(summary_data.all_allergies, start=1):
                    try:
                        allergen = str(allergy.get("allergen", "Unknown"))
                        severity = str(allergy.get("severity", "") or "—").upper()
                        reaction = str(allergy.get("reaction", "") or "—")
                        row_bg = (
                            C_RED_LT
                            if severity in ("SEVERE", "HIGH", "LIFE-THREATENING")
                            else (C_ROW_ALT if i % 2 == 0 else C_WHITE)
                        )
                        allergy_rows.append(
                            [
                                Paragraph(
                                    f"<b>{allergen}</b>",
                                    ParagraphStyle(
                                        "AC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    severity,
                                    ParagraphStyle(
                                        "AC",
                                        parent=styles["Normal"],
                                        fontSize=8,
                                        textColor=(
                                            C_RED
                                            if severity
                                            in ("SEVERE", "HIGH", "LIFE-THREATENING")
                                            else colors.black
                                        ),
                                    ),
                                ),
                                Paragraph(
                                    reaction,
                                    ParagraphStyle(
                                        "AC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                            ]
                        )
                        if row_bg != C_WHITE:
                            allergy_style_cmds.append(
                                ("BACKGROUND", (0, i), (-1, i), row_bg)
                            )
                    except Exception as ae:
                        print(f"⚠️  Allergy format error: {ae}")
                allergy_tbl = Table(
                    allergy_rows, colWidths=[2.5 * inch, 1.5 * inch, 2.5 * inch]
                )
                allergy_tbl.setStyle(TableStyle(allergy_style_cmds))
                story.append(allergy_tbl)
            else:
                story.append(empty_note("No allergies recorded."))
            story.append(Spacer(1, 0.15 * inch))

            # ── VITAL SIGNS ───────────────────────────────────────────────
            if summary_data.all_vitals and len(summary_data.all_vitals) > 0:
                story.append(section_header("VITAL SIGNS", ""))
                story.append(Spacer(1, 0.05 * inch))
                vital_rows = [
                    [
                        Paragraph(
                            "<b>Date</b>",
                            ParagraphStyle(
                                "VH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>BP</b>",
                            ParagraphStyle(
                                "VH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>HR</b>",
                            ParagraphStyle(
                                "VH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Temp</b>",
                            ParagraphStyle(
                                "VH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>SpO2</b>",
                            ParagraphStyle(
                                "VH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Wt / Ht</b>",
                            ParagraphStyle(
                                "VH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>BMI</b>",
                            ParagraphStyle(
                                "VH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                    ]
                ]
                for i, vital in enumerate(summary_data.all_vitals):
                    try:
                        date_str = "—"
                        if (
                            hasattr(vital, "measurement_date")
                            and vital.measurement_date
                        ):
                            try:
                                raw_d = str(vital.measurement_date)
                                date_str = datetime.fromisoformat(
                                    raw_d.replace("Z", "+00:00")
                                ).strftime("%d %b %Y")
                            except:
                                date_str = str(vital.measurement_date)[:10]

                        bp_val = "—"
                        if (
                            hasattr(vital, "systolic_bp")
                            and hasattr(vital, "diastolic_bp")
                            and vital.systolic_bp
                            and vital.diastolic_bp
                        ):
                            bp_val = f"{vital.systolic_bp}/{vital.diastolic_bp}"

                        hr_val = (
                            str(vital.heart_rate)
                            if hasattr(vital, "heart_rate") and vital.heart_rate
                            else "—"
                        )
                        t_unit = getattr(vital, "temperature_unit", "") or ""
                        temp_val = (
                            f"{vital.temperature}{t_unit}"
                            if hasattr(vital, "temperature") and vital.temperature
                            else "—"
                        )
                        spo2_val = (
                            f"{vital.oxygen_saturation}%"
                            if hasattr(vital, "oxygen_saturation")
                            and vital.oxygen_saturation
                            else "—"
                        )
                        w_unit = getattr(vital, "weight_unit", "") or ""
                        h_unit = getattr(vital, "height_unit", "") or ""
                        wh_val = (
                            ""
                            if not (hasattr(vital, "weight") and vital.weight)
                            else f"{vital.weight}{w_unit}"
                        ) + (
                            ""
                            if not (hasattr(vital, "height") and vital.height)
                            else f" / {vital.height}{h_unit}"
                        )
                        wh_val = wh_val.strip(" /") or "—"
                        bmi_val = (
                            str(vital.bmi)
                            if hasattr(vital, "bmi") and vital.bmi
                            else "—"
                        )

                        vital_rows.append(
                            [
                                Paragraph(
                                    date_str,
                                    ParagraphStyle(
                                        "VC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    bp_val,
                                    ParagraphStyle(
                                        "VC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    hr_val,
                                    ParagraphStyle(
                                        "VC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    temp_val,
                                    ParagraphStyle(
                                        "VC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    spo2_val,
                                    ParagraphStyle(
                                        "VC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    wh_val,
                                    ParagraphStyle(
                                        "VC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    bmi_val,
                                    ParagraphStyle(
                                        "VC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                            ]
                        )
                    except Exception as ve:
                        print(f"⚠️  Vital format error: {ve}")
                        import traceback

                        traceback.print_exc()

                vital_tbl = Table(
                    vital_rows,
                    colWidths=[
                        1.1 * inch,
                        0.85 * inch,
                        0.65 * inch,
                        0.75 * inch,
                        0.65 * inch,
                        1.3 * inch,
                        0.65 * inch,
                    ],
                )
                vital_style_cmds = [
                    ("BACKGROUND", (0, 0), (-1, 0), C_NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
                ]
                for i in range(1, len(vital_rows)):
                    if i % 2 == 0:
                        vital_style_cmds.append(
                            ("BACKGROUND", (0, i), (-1, i), C_ROW_ALT)
                        )
                vital_tbl.setStyle(TableStyle(vital_style_cmds))
                story.append(vital_tbl)
                story.append(Spacer(1, 0.15 * inch))

            # ── LAB RESULTS ───────────────────────────────────────────────
            if summary_data.all_lab_results and len(summary_data.all_lab_results) > 0:
                story.append(section_header("LAB RESULTS", ""))
                story.append(Spacer(1, 0.05 * inch))
                lab_rows = [
                    [
                        Paragraph(
                            "<b>Test</b>",
                            ParagraphStyle(
                                "LH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Result</b>",
                            ParagraphStyle(
                                "LH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Unit</b>",
                            ParagraphStyle(
                                "LH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Ref Range</b>",
                            ParagraphStyle(
                                "LH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Date</b>",
                            ParagraphStyle(
                                "LH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                        Paragraph(
                            "<b>Flag</b>",
                            ParagraphStyle(
                                "LH",
                                parent=styles["Normal"],
                                fontSize=8,
                                fontName="Helvetica-Bold",
                                textColor=C_NAVY,
                            ),
                        ),
                    ]
                ]
                lab_style_cmds = [
                    ("BACKGROUND", (0, 0), (-1, 0), C_NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
                ]
                for i, lab in enumerate(summary_data.all_lab_results, start=1):
                    try:
                        is_abn = getattr(lab, "is_abnormal", False)
                        flag_txt = str(
                            getattr(lab, "abnormal_flag", "")
                            or ("ABN" if is_abn else "—")
                        )
                        row_bg = (
                            C_RED_LT
                            if is_abn
                            else (C_ROW_ALT if i % 2 == 0 else C_WHITE)
                        )
                        lab_rows.append(
                            [
                                Paragraph(
                                    f"<b>{str(lab.test_name)}</b>",
                                    ParagraphStyle(
                                        "LC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    str(lab.value or "—"),
                                    ParagraphStyle(
                                        "LC",
                                        parent=styles["Normal"],
                                        fontSize=8,
                                        textColor=(C_RED if is_abn else colors.black),
                                    ),
                                ),
                                Paragraph(
                                    str(getattr(lab, "unit", None) or "—"),
                                    ParagraphStyle(
                                        "LC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    str(getattr(lab, "reference_range", None) or "—"),
                                    ParagraphStyle(
                                        "LC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    str(getattr(lab, "test_date", None) or "—")[:10],
                                    ParagraphStyle(
                                        "LC", parent=styles["Normal"], fontSize=8
                                    ),
                                ),
                                Paragraph(
                                    flag_txt,
                                    ParagraphStyle(
                                        "LC",
                                        parent=styles["Normal"],
                                        fontSize=8,
                                        textColor=(C_RED if is_abn else C_GREEN),
                                    ),
                                ),
                            ]
                        )
                        if row_bg != C_WHITE:
                            lab_style_cmds.append(
                                ("BACKGROUND", (0, i), (-1, i), row_bg)
                            )
                    except Exception as le:
                        print(f"⚠️  Lab format error: {le}")
                lab_tbl = Table(
                    lab_rows,
                    colWidths=[
                        1.8 * inch,
                        0.9 * inch,
                        0.7 * inch,
                        1.1 * inch,
                        0.9 * inch,
                        0.6 * inch,
                    ],
                )
                lab_tbl.setStyle(TableStyle(lab_style_cmds))
                story.append(lab_tbl)
                story.append(Spacer(1, 0.15 * inch))

            # ── PROCEDURES ────────────────────────────────────────────────
            if hasattr(summary_data, "all_procedures") and summary_data.all_procedures:
                story.append(section_header("PROCEDURES", ""))
                story.append(Spacer(1, 0.05 * inch))
                for proc in summary_data.all_procedures:
                    try:
                        proc_text = f"<b>{proc.get('procedure_name', 'Unknown')}</b>"
                        if proc.get("performed_date"):
                            proc_text += f"  |  {str(proc['performed_date'])[:10]}"
                        if proc.get("provider"):
                            proc_text += f"  |  Dr. {proc['provider']}"
                        if proc.get("outcome"):
                            proc_text += f"  |  {proc['outcome']}"
                        story.append(body_para(f"• {proc_text}"))
                    except Exception as pe:
                        print(f"⚠️  Procedure format error: {pe}")
                story.append(Spacer(1, 0.15 * inch))

            # ── IMMUNIZATIONS ─────────────────────────────────────────────
            if summary_data.immunizations and len(summary_data.immunizations) > 0:
                story.append(section_header("IMMUNIZATIONS", ""))
                story.append(Spacer(1, 0.05 * inch))
                for imm in summary_data.immunizations:
                    try:
                        imm_text = f"<b>{imm.get('vaccine_name', 'Unknown')}</b>"
                        if imm.get("administration_date"):
                            imm_text += f"  |  {str(imm['administration_date'])[:10]}"
                        if imm.get("dose_number"):
                            imm_text += f"  |  Dose {imm['dose_number']}"
                        if imm.get("manufacturer"):
                            imm_text += f"  |  {imm['manufacturer']}"
                        story.append(body_para(f"• {imm_text}"))
                    except Exception as ie:
                        print(f"⚠️  Immunization format error: {ie}")
                story.append(Spacer(1, 0.15 * inch))

            # ── PROVIDER & EMERGENCY CONTACT ──────────────────────────────
            has_pcp = (
                hasattr(summary_data, "primary_care_physician")
                and summary_data.primary_care_physician
            )
            has_ec = (
                hasattr(summary_data, "emergency_contact")
                and summary_data.emergency_contact
            )
            if has_pcp or has_ec:
                story.append(section_header("PROVIDER & EMERGENCY CONTACT", ""))
                story.append(Spacer(1, 0.05 * inch))
                if has_pcp:
                    story.append(
                        body_para(
                            f"<b>Primary Care Physician:</b>  {str(summary_data.primary_care_physician)}"
                        )
                    )
                if has_ec:
                    ec = summary_data.emergency_contact
                    try:
                        ec_text = "<b>Emergency Contact:</b>  "
                        if hasattr(ec, "name") and ec.name:
                            ec_text += str(ec.name)
                        if hasattr(ec, "phone") and ec.phone:
                            ec_text += f"  |  {str(ec.phone)}"
                        story.append(body_para(ec_text))
                    except Exception as ec_err:
                        print(f"⚠️  EC format error: {ec_err}")
                story.append(Spacer(1, 0.15 * inch))

            # ── FOOTER ────────────────────────────────────────────────────
            story.append(Spacer(1, 0.1 * inch))
            footer_divider = Table([[""]], colWidths=[6.5 * inch])
            footer_divider.setStyle(
                TableStyle(
                    [
                        ("LINEABOVE", (0, 0), (-1, -1), 1, C_NAVY),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(footer_divider)
            story.append(Spacer(1, 0.06 * inch))

            footer_rows = [
                [
                    Paragraph(
                        "Medrix Medical ID System  |  This document is for informational purposes only and does not replace clinical consultation.",
                        ParagraphStyle(
                            "FootL",
                            parent=styles["Normal"],
                            fontSize=7,
                            textColor=C_GREY_TEXT,
                        ),
                    ),
                    Paragraph(
                        f"Generated {datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC",
                        ParagraphStyle(
                            "FootR",
                            parent=styles["Normal"],
                            fontSize=7,
                            textColor=C_GREY_TEXT,
                            alignment=TA_RIGHT,
                        ),
                    ),
                ]
            ]
            footer_tbl = Table(footer_rows, colWidths=[4.5 * inch, 2.0 * inch])
            footer_tbl.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(footer_tbl)

            # ── BUILD ─────────────────────────────────────────────────────
            print(f"🔨 Building PDF document...")
            doc.build(story)

            pdf_bytes = buffer.getvalue()
            buffer.close()

            print(f"✓ PDF generated successfully: {len(pdf_bytes)} bytes")
            return pdf_bytes

        except Exception as pdf_error:
            print(f"❌ CRITICAL PDF generation error: {pdf_error}")
            import traceback

            traceback.print_exc()
            raise

    def generate_qr_code(self, data: str, size: int = 300) -> bytes:
        """
        Generate QR code image.

        Args:
            data: Data to encode in QR code
            size: Image size in pixels

        Returns:
            PNG image bytes
        """
        from PIL import Image as PILImage

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to PIL Image if needed and resize
        try:
            # PIL 10.0+ uses Image.Resampling.LANCZOS, older versions use Image.LANCZOS
            resize_filter = (
                PILImage.Resampling.LANCZOS
                if hasattr(PILImage, "Resampling")
                else PILImage.LANCZOS
            )
        except AttributeError:
            resize_filter = 1  # Fallback to LANCZOS constant value

        img = img.resize((size, size), resize_filter)

        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_bytes = buffer.getvalue()
        buffer.close()

        return qr_bytes
