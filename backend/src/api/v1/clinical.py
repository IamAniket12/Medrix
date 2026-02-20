"""Clinical data retrieval endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from src.core.dependencies import get_db
from src.models import (
    Document,
    DocumentProcessingResult,
    DocumentSummary,
    ClinicalCondition,
    ClinicalMedication,
    ClinicalAllergy,
    ClinicalLabResult,
    ClinicalVitalSign,
    ClinicalProcedure,
    ClinicalImmunization,
    TimelineEvent,
)

router = APIRouter(prefix="/clinical", tags=["clinical"])


# ============================================================
# DOCUMENTS LIST & DETAIL
# ============================================================


@router.get("/documents/{user_id}")
async def get_user_documents(
    user_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Get all documents for a user with summary data.
    Perfect for the documents list page.
    """
    documents = (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.uploaded_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for doc in documents:
        # Get summary
        summary = (
            db.query(DocumentSummary)
            .filter(DocumentSummary.document_id == doc.id)
            .first()
        )

        # Count clinical data
        conditions_count = (
            db.query(ClinicalCondition)
            .filter(
                ClinicalCondition.document_id == doc.id,
                ClinicalCondition.deleted_at.is_(None),
            )
            .count()
        )
        medications_count = (
            db.query(ClinicalMedication)
            .filter(
                ClinicalMedication.document_id == doc.id,
                ClinicalMedication.deleted_at.is_(None),
            )
            .count()
        )
        labs_count = (
            db.query(ClinicalLabResult)
            .filter(
                ClinicalLabResult.document_id == doc.id,
                ClinicalLabResult.deleted_at.is_(None),
            )
            .count()
        )

        results.append(
            {
                "id": doc.id,
                "filename": doc.original_name,
                "file_path": doc.file_path,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "uploaded_at": doc.uploaded_at.isoformat(),
                "document_type": doc.document_type,
                "document_date": (
                    doc.document_date.isoformat() if doc.document_date else None
                ),
                "extraction_status": doc.extraction_status,
                "summary": {
                    "brief": summary.brief_summary if summary else None,
                    "urgency_level": summary.urgency_level if summary else "routine",
                },
                "counts": {
                    "conditions": conditions_count,
                    "medications": medications_count,
                    "labs": labs_count,
                },
            }
        )

    return {
        "success": True,
        "count": len(results),
        "documents": results,
    }


@router.get("/documents/{user_id}/{document_id}")
async def get_document_details(
    user_id: str,
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    Get complete document details with all extracted clinical data.
    Perfect for the document detail view.
    """
    # Get document
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user_id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get processing result
    processing = (
        db.query(DocumentProcessingResult)
        .filter(DocumentProcessingResult.document_id == document_id)
        .first()
    )

    # Get summary
    summary = (
        db.query(DocumentSummary)
        .filter(DocumentSummary.document_id == document_id)
        .first()
    )

    # Get all clinical data
    conditions = (
        db.query(ClinicalCondition)
        .filter(
            ClinicalCondition.document_id == document_id,
            ClinicalCondition.deleted_at.is_(None),
        )
        .all()
    )

    medications = (
        db.query(ClinicalMedication)
        .filter(
            ClinicalMedication.document_id == document_id,
            ClinicalMedication.deleted_at.is_(None),
        )
        .all()
    )

    allergies = (
        db.query(ClinicalAllergy)
        .filter(
            ClinicalAllergy.document_id == document_id,
            ClinicalAllergy.deleted_at.is_(None),
        )
        .all()
    )

    lab_results = (
        db.query(ClinicalLabResult)
        .filter(
            ClinicalLabResult.document_id == document_id,
            ClinicalLabResult.deleted_at.is_(None),
        )
        .all()
    )

    vital_signs = (
        db.query(ClinicalVitalSign)
        .filter(
            ClinicalVitalSign.document_id == document_id,
            ClinicalVitalSign.deleted_at.is_(None),
        )
        .all()
    )

    procedures = (
        db.query(ClinicalProcedure)
        .filter(
            ClinicalProcedure.document_id == document_id,
            ClinicalProcedure.deleted_at.is_(None),
        )
        .all()
    )

    immunizations = (
        db.query(ClinicalImmunization)
        .filter(
            ClinicalImmunization.document_id == document_id,
            ClinicalImmunization.deleted_at.is_(None),
        )
        .all()
    )

    timeline = (
        db.query(TimelineEvent)
        .filter(
            TimelineEvent.document_id == document_id,
            TimelineEvent.deleted_at.is_(None),
        )
        .order_by(TimelineEvent.event_date.desc())
        .all()
    )

    # Format response
    return {
        "success": True,
        "document": {
            "id": document.id,
            "filename": document.original_name,
            "file_path": document.file_path,
            "file_size": document.file_size,
            "mime_type": document.mime_type,
            "uploaded_at": document.uploaded_at.isoformat(),
            "document_type": document.document_type,
            "document_date": (
                document.document_date.isoformat() if document.document_date else None
            ),
            "extraction_status": document.extraction_status,
        },
        "summary": (
            {
                "brief": summary.brief_summary if summary else None,
                "clinical_overview": summary.clinical_overview if summary else None,
                "clinical_significance": (
                    summary.clinical_significance if summary else None
                ),
                "urgency_level": summary.urgency_level if summary else "routine",
                "key_findings": summary.key_findings if summary else [],
                "treatment_plan": summary.treatment_plan if summary else {},
                "action_items": summary.action_items if summary else [],
            }
            if summary
            else None
        ),
        "processing": (
            {
                "quality_score": processing.quality_score if processing else None,
                "is_valid": processing.is_valid if processing else None,
                "validation_issues": processing.validation_issues if processing else [],
            }
            if processing
            else None
        ),
        "clinical_data": {
            "conditions": [
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "diagnosed_date": (
                        c.diagnosed_date.isoformat() if c.diagnosed_date else None
                    ),
                    "severity": c.severity,
                    "body_site": c.body_site,
                    "icd10_code": c.icd10_code,
                    "notes": c.notes,
                }
                for c in conditions
            ],
            "medications": [
                {
                    "id": m.id,
                    "name": m.name,
                    "dosage": m.dosage,
                    "frequency": m.frequency,
                    "route": m.route,
                    "start_date": m.start_date.isoformat() if m.start_date else None,
                    "end_date": m.end_date.isoformat() if m.end_date else None,
                    "prescriber": m.prescriber,
                    "indication": m.indication,
                    "is_active": m.is_active,
                    "rxnorm_code": m.rxnorm_code,
                    "notes": m.notes,
                }
                for m in medications
            ],
            "allergies": [
                {
                    "id": a.id,
                    "allergen": a.allergen,
                    "reaction": a.reaction,
                    "severity": a.severity,
                    "allergy_type": a.allergy_type,
                    "verified_date": (
                        a.verified_date.isoformat() if a.verified_date else None
                    ),
                    "is_active": a.is_active,
                    "notes": a.notes,
                }
                for a in allergies
            ],
            "lab_results": [
                {
                    "id": l.id,
                    "test_name": l.test_name,
                    "value": l.value,
                    "unit": l.unit,
                    "reference_range": l.reference_range,
                    "is_abnormal": l.is_abnormal,
                    "abnormal_flag": l.abnormal_flag,
                    "test_date": l.test_date.isoformat() if l.test_date else None,
                    "ordering_provider": l.ordering_provider,
                    "lab_facility": l.lab_facility,
                    "loinc_code": l.loinc_code,
                    "notes": l.notes,
                }
                for l in lab_results
            ],
            "vital_signs": [
                {
                    "id": v.id,
                    "measurement_date": (
                        v.measurement_date.isoformat() if v.measurement_date else None
                    ),
                    "systolic_bp": v.systolic_bp,
                    "diastolic_bp": v.diastolic_bp,
                    "heart_rate": v.heart_rate,
                    "respiratory_rate": v.respiratory_rate,
                    "temperature": v.temperature,
                    "temperature_unit": v.temperature_unit,
                    "oxygen_saturation": v.oxygen_saturation,
                    "weight": v.weight,
                    "weight_unit": v.weight_unit,
                    "height": v.height,
                    "height_unit": v.height_unit,
                    "bmi": v.bmi,
                    "notes": v.notes,
                }
                for v in vital_signs
            ],
            "procedures": [
                {
                    "id": p.id,
                    "procedure_name": p.procedure_name,
                    "performed_date": (
                        p.performed_date.isoformat() if p.performed_date else None
                    ),
                    "provider": p.provider,
                    "facility": p.facility,
                    "body_site": p.body_site,
                    "indication": p.indication,
                    "outcome": p.outcome,
                    "cpt_code": p.cpt_code,
                    "icd10_pcs_code": p.icd10_pcs_code,
                    "notes": p.notes,
                }
                for p in procedures
            ],
            "immunizations": [
                {
                    "id": i.id,
                    "vaccine_name": i.vaccine_name,
                    "administration_date": (
                        i.administration_date.isoformat()
                        if i.administration_date
                        else None
                    ),
                    "dose_number": i.dose_number,
                    "site": i.site,
                    "route": i.route,
                    "administered_by": i.administered_by,
                    "facility": i.facility,
                    "manufacturer": i.manufacturer,
                    "cvx_code": i.cvx_code,
                    "lot_number": i.lot_number,
                    "expiration_date": (
                        i.expiration_date.isoformat() if i.expiration_date else None
                    ),
                    "notes": i.notes,
                }
                for i in immunizations
            ],
        },
        "timeline": [
            {
                "id": t.id,
                "event_type": t.event_type,
                "event_date": t.event_date.isoformat() if t.event_date else None,
                "title": t.event_title,
                "description": t.event_description,
                "importance": t.importance,
                "related_condition_id": t.related_condition_id,
                "related_medication_id": t.related_medication_id,
            }
            for t in timeline
        ],
    }


