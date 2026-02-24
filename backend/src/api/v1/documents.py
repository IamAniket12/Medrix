"""
Document upload and analysis API endpoints (v1) - Multi-Agent System.
"""

import asyncio
from datetime import datetime
from fastapi import (
    APIRouter,
    BackgroundTasks,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
)
from sqlalchemy.orm import Session

from src.core.config import Settings
from src.core.dependencies import get_settings_dependency
from src.core.database import get_db, SessionLocal
from src.schemas.document import (
    DocumentUploadResponse,
    FileInfo,
    ExtractedData,
    TestResponse,
)
from src.services.storage_service import StorageService
from src.services.agent_orchestrator import MedicalDocumentAgentOrchestrator
from src.services.agent_persistence_service import AgentPersistenceService
from src.utils.file_utils import (
    is_allowed_file,
    format_file_size,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/progress/{job_id}")
async def get_processing_progress(job_id: str):
    """
    Get real-time progress for a document processing job.

    Args:
        job_id: Unique job ID returned from upload endpoint

    Returns:
        Progress information including current stage and status
    """
    progress = MedicalDocumentAgentOrchestrator.get_progress(job_id)

    if not progress:
        print(f"[Progress API] Job {job_id} not found")
        raise HTTPException(
            status_code=404, detail=f"No processing job found with ID: {job_id}"
        )

    print(
        f"[Progress API] Returning progress for {job_id}: {progress['current_stage']} ({progress['overall_status']})"
    )
    return progress


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    settings: Settings = Depends(get_settings_dependency),
    db: Session = Depends(get_db),
):
    """
    Upload a medical document (PDF or image) and analyze using Multi-Agent System.

    Returns immediately with a job_id for progress tracking.
    All agent processing runs in the background.
    """

    # Validate file extension
    if not is_allowed_file(file.filename, settings.allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.allowed_extensions)}",
        )

    # Read and validate file size
    file_content = await file.read()
    file_size = len(file_content)

    max_size = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB",
        )

    await file.seek(0)

    try:
        # Step 1: Upload to Google Cloud Storage (fast, do synchronously)
        storage_service = StorageService(settings)

        print(f"\n{'='*60}")
        print(f"📤 UPLOADING TO GOOGLE CLOUD STORAGE")
        print(f"{'='*60}")
        print(f"Original filename: {file.filename}")
        print(f"File size: {format_file_size(file_size)}")

        upload_result = await storage_service.save_file(
            file.file, file.filename, folder="documents"
        )

        if not upload_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {upload_result.get('error')}",
            )

        gcs_url = upload_result["url"]
        print(f"✓ Uploaded to: {gcs_url}")
        print(f"{'='*60}\n")

        # Step 2: Generate job_id and initialise progress tracking BEFORE returning
        orchestrator = MedicalDocumentAgentOrchestrator(settings)
        job_id = MedicalDocumentAgentOrchestrator.create_job_id(file.filename)

        # Initialise the progress store entry so polling works immediately
        MedicalDocumentAgentOrchestrator.update_progress(
            job_id, "validating", "in_progress", "Starting document validation..."
        )

        file_type = "PDF" if file.filename.lower().endswith(".pdf") else "Image"
        original_filename = file.filename

        # Step 3: Schedule the heavy agent work as a background task
        background_tasks.add_task(
            _run_agent_pipeline,
            job_id=job_id,
            file_content=file_content,
            filename=original_filename,
            file_type=file_type,
            file_size=file_size,
            upload_result=upload_result,
            settings=settings,
            user_id=user_id,
        )

        # Step 4: Return immediately so the frontend can start polling
        file_info_response = FileInfo(
            original_filename=original_filename,
            saved_filename=upload_result["file_path"],
            file_size=format_file_size(file_size),
            file_type=file_type,
            upload_timestamp=datetime.now(),
        )

        return DocumentUploadResponse(
            success=True,
            message="Document uploaded. Processing started in background.",
            job_id=job_id,
            file_info=file_info_response,
            extracted_data=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def _run_agent_pipeline(
    job_id: str,
    file_content: bytes,
    filename: str,
    file_type: str,
    file_size: int,
    upload_result: dict,
    settings: Settings,
    user_id: str,
):
    """
    Background task: run 4-agent pipeline and save results to DB.
    Creates its own DB session so it's independent of the request lifecycle.
    """
    import uuid
    import json
    from src.services.database_service import DatabaseService

    db = SessionLocal()
    try:
        document_id_uuid = uuid.uuid4()

        # Ensure user exists
        db_service = DatabaseService(db)
        user = db_service.get_or_create_user(
            user_id, email="demo@medrix.ai", name="Demo User"
        )

        orchestrator = MedicalDocumentAgentOrchestrator(settings)

        print(f"\n{'='*60}")
        print(f"🤖 4-AGENT PIPELINE STARTED (background)")
        print(f"{'='*60}")
        print(f"Job ID: {job_id}")
        print(f"Document: {filename}")

        agent_results = await orchestrator.process_document(
            image_bytes=file_content,
            filename=filename,
            file_type=file_type,
            db_session=db,
            user_id=user_id,
            document_id=None,
            job_id=job_id,
        )

        if agent_results.get("validation_failed", False):
            validation = agent_results.get("validation", {})
            issues = validation.get("validation", {}).get(
                "issues", ["Document validation failed"]
            )
            print(f"❌ DOCUMENT REJECTED: {', '.join(issues)}")
            MedicalDocumentAgentOrchestrator.update_progress(
                job_id, "failed", "failed", "Document rejected", error=", ".join(issues)
            )
            return

        if not agent_results.get("success", False):
            error = agent_results.get("error", "Unknown error")
            print(f"❌ PIPELINE FAILED: {error}")
            MedicalDocumentAgentOrchestrator.update_progress(
                job_id, "failed", "failed", "Pipeline failed", error=error
            )
            return

        # ── Save to Database ─────────────────────────────────────────────
        validation = agent_results.get("validation", {})
        clinical_data = agent_results.get("clinical_data", {})
        summaries = agent_results.get("summaries", {})
        relationships = agent_results.get("relationships", {})

        doc_metadata = validation.get("document_metadata", {})
        doc_type = doc_metadata.get("document_type", "unknown")
        document_id = str(document_id_uuid)

        try:
            doc_date = doc_metadata.get("document_date")
            if doc_date:
                try:
                    from datetime import datetime as dt

                    doc_date = (
                        dt.strptime(doc_date, "%Y-%m-%d")
                        if isinstance(doc_date, str)
                        else doc_date
                    )
                except Exception:
                    doc_date = None

            document = db_service.create_document(
                document_id=document_id,
                user_id=user_id,
                filename=upload_result["file_path"],
                original_name=filename,
                mime_type="image/jpeg" if file_type == "Image" else "application/pdf",
                file_size=file_size,
                file_path=upload_result["file_path"],
                document_type=doc_type,
                document_date=doc_date,
            )
            print(f"✓ Document saved: {document.id}")

            persistence_service = AgentPersistenceService(db)
            persistence_service.save_agent_results(
                document_id=document_id,
                user_id=user_id,
                agent_results=agent_results,
            )

            db_service.update_document_extraction(
                document_id=document_id,
                status="completed",
                extracted_data=agent_results,
            )
            print(f"✓ Database save complete")

            # ── Embeddings ───────────────────────────────────────────────
            try:
                from src.services.embeddings_service import embeddings_service
                from src.models import TimelineEvent

                doc_embeddings = embeddings_service.create_document_embeddings(
                    db=db,
                    document=document,
                    summaries=summaries,
                    clinical_data=clinical_data,
                )
                print(f"✓ Created {len(doc_embeddings)} document embeddings")

                timeline_events = (
                    db.query(TimelineEvent)
                    .filter(
                        TimelineEvent.document_id == document_id,
                        TimelineEvent.deleted_at.is_(None),
                    )
                    .all()
                )
                temporal_events = summaries.get("agent_context", {}).get(
                    "temporal_events", []
                )
                for event in timeline_events:
                    search_summary = next(
                        (
                            te.get("search_summary")
                            for te in temporal_events
                            if te.get("event_title") == event.event_title
                            or te.get("event_type") == event.event_type
                        ),
                        None,
                    )
                    embeddings_service.create_timeline_event_embedding(
                        db=db, event=event, search_summary=search_summary
                    )

                from src.models.clinical_data import (
                    ClinicalCondition as ClinicalConditionModel,
                    ClinicalMedication as ClinicalMedicationModel,
                    ClinicalLabResult as ClinicalLabResultModel,
                    ClinicalProcedure as ClinicalProcedureModel,
                )

                entity_count = 0
                for cond in (
                    db.query(ClinicalConditionModel)
                    .filter(
                        ClinicalConditionModel.document_id == document_id,
                        ClinicalConditionModel.deleted_at.is_(None),
                    )
                    .all()
                ):
                    try:
                        embeddings_service.create_clinical_entity_embedding(
                            db=db,
                            user_id=user_id,
                            entity_type="condition",
                            entity_id=cond.id,
                            entity_name=cond.name,
                            entity_data={
                                "icd10_code": cond.icd10_code,
                                "status": cond.status,
                                "severity": cond.severity,
                                "body_site": cond.body_site,
                            },
                        )
                        entity_count += 1
                    except Exception:
                        pass
                for med in (
                    db.query(ClinicalMedicationModel)
                    .filter(
                        ClinicalMedicationModel.document_id == document_id,
                        ClinicalMedicationModel.deleted_at.is_(None),
                    )
                    .all()
                ):
                    try:
                        embeddings_service.create_clinical_entity_embedding(
                            db=db,
                            user_id=user_id,
                            entity_type="medication",
                            entity_id=med.id,
                            entity_name=med.name,
                            entity_data={
                                "dosage": med.dosage,
                                "frequency": med.frequency,
                                "route": med.route,
                                "status": "active" if med.is_active else "stopped",
                            },
                        )
                        entity_count += 1
                    except Exception:
                        pass
                for lab in (
                    db.query(ClinicalLabResultModel)
                    .filter(
                        ClinicalLabResultModel.document_id == document_id,
                        ClinicalLabResultModel.deleted_at.is_(None),
                    )
                    .all()
                ):
                    try:
                        embeddings_service.create_clinical_entity_embedding(
                            db=db,
                            user_id=user_id,
                            entity_type="lab_result",
                            entity_id=lab.id,
                            entity_name=lab.test_name,
                            entity_data={
                                "value": lab.value,
                                "unit": lab.unit,
                                "is_abnormal": lab.is_abnormal,
                            },
                        )
                        entity_count += 1
                    except Exception:
                        pass
                for proc in (
                    db.query(ClinicalProcedureModel)
                    .filter(
                        ClinicalProcedureModel.document_id == document_id,
                        ClinicalProcedureModel.deleted_at.is_(None),
                    )
                    .all()
                ):
                    try:
                        embeddings_service.create_clinical_entity_embedding(
                            db=db,
                            user_id=user_id,
                            entity_type="procedure",
                            entity_id=proc.id,
                            entity_name=proc.procedure_name,
                            entity_data={"outcome": proc.outcome},
                        )
                        entity_count += 1
                    except Exception:
                        pass
                print(f"✓ Created {entity_count} clinical entity embeddings")

            except Exception as embed_error:
                print(f"⚠️  Embeddings failed (non-critical): {embed_error}")

        except Exception as db_error:
            print(f"⚠️  Database save failed: {db_error}")
            import traceback

            traceback.print_exc()

        print(f"\n{'='*60}")
        print(f"✅ BACKGROUND PIPELINE COMPLETE — Job: {job_id}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"❌ Background pipeline error for job {job_id}: {e}")
        import traceback

        traceback.print_exc()
        MedicalDocumentAgentOrchestrator.update_progress(
            job_id, "failed", "failed", "Unexpected error", error=str(e)
        )
    finally:
        db.close()


@router.get("/test", response_model=TestResponse)
async def test_endpoint(settings: Settings = Depends(get_settings_dependency)):
    """Test endpoint to verify API configuration."""
    return TestResponse(
        status="ok",
        message="Multi-Agent Document Analysis API is running",
        config={
            "project": settings.google_cloud_project,
            "location": settings.vertex_ai_location,
            "gcs_bucket": settings.gcs_bucket_name,
            "max_file_size_mb": settings.max_file_size_mb,
            "allowed_extensions": list(settings.allowed_extensions),
            "agents": ["Classifier", "Extractor", "Summarizer"],
        },
    )
