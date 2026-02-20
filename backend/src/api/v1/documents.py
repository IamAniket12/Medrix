"""
Document upload and analysis API endpoints (v1) - Multi-Agent System.
"""

from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from src.core.config import Settings
from src.core.dependencies import get_settings_dependency
from src.core.database import get_db
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


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings_dependency),
    db: Session = Depends(get_db),
):
    """
    Upload a medical document (PDF or image) and analyze using Multi-Agent System.

    Flow:
    1. Validate file type and size
    2. Upload to Google Cloud Storage
    3. Process through 3 specialized agents:
       - Validation Agent: Document quality & metadata
       - Extraction Agent: Medical data (conditions, meds, labs, vitals)
       - Summary Agent: Human-readable summary with agent context
    4. Save results to database (all tables)
    5. Return combined results

    Args:
        file: Uploaded file (PDF, JPG, PNG)
        settings: Application settings
        db: Database session

    Returns:
        DocumentUploadResponse with file info and multi-agent analysis
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
        # Step 1: Upload to Google Cloud Storage
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

        # Step 2: Process with 5-Agent System
        # Pass the image bytes directly to MedGemma (no need to download from GCS)
        file_type = "PDF" if file.filename.lower().endswith(".pdf") else "Image"

        # Generate user and document IDs (in production, use actual auth)
        import uuid

        user_id = "demo_user_001"  # TODO: Replace with actual user ID from auth
        document_id_uuid = uuid.uuid4()

        # Ensure user exists before processing
        from src.services.database_service import DatabaseService

        db_service = DatabaseService(db)
        user = db_service.get_or_create_user(
            user_id, email="demo@medrix.ai", name="Demo User"
        )

        orchestrator = MedicalDocumentAgentOrchestrator(settings)
        agent_results = await orchestrator.process_document(
            image_bytes=file_content,
            filename=file.filename,
            file_type=file_type,
            db_session=db,
            user_id=user_id,
            document_id=None,  # Will be created after validation passes
        )

        # Check if validation failed
        if agent_results.get("validation_failed", False):
            validation = agent_results.get("validation", {})
            issues = validation.get("validation", {}).get(
                "issues", ["Document validation failed"]
            )

            print(f"\n{'='*60}")
            print(f"❌ DOCUMENT REJECTED")
            print(f"{'='*60}\n")

            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Document validation failed",
                    "issues": issues,
                    "validation_details": validation,
                },
            )

        if not agent_results["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Agent processing failed: {agent_results.get('error')}",
            )

        # Step 3: Extract agent results (4-AGENT STRUCTURE)
        validation = agent_results.get("validation", {})
        clinical_data = agent_results.get("clinical_data", {})
        summaries = agent_results.get("summaries", {})
        relationships = agent_results.get("relationships", {})
        needs_review = agent_results.get("needs_review", False)

        # Extract metadata from validation
        doc_metadata = validation.get("document_metadata", {})
        doc_type = doc_metadata.get("document_type", "unknown")

        # Display results
        print(f"\n{'='*60}")
        print(f"[OK] 4-AGENT ANALYSIS COMPLETE")
        print(f"{'='*60}\n")

        print("[DOC] DOCUMENT VALIDATION:")
        print(f"  Type: {doc_type}")
        print(f"  Date: {doc_metadata.get('document_date', 'N/A')}")
        print(
            f"  Quality Score: {validation.get('validation', {}).get('quality_score', 0)}"
        )

        print("\n[CLINICAL] CLINICAL DATA EXTRACTION:")
        print(f"  Conditions: {len(clinical_data.get('conditions', []))}")
        print(f"  Medications: {len(clinical_data.get('medications', []))}")
        print(f"  Allergies: {len(clinical_data.get('allergies', []))}")
        print(f"  Lab Results: {len(clinical_data.get('lab_results', []))}")
        print(f"  Vital Signs: {len(clinical_data.get('vital_signs', []))}")

        print("\n[SUMMARY] INTELLIGENT SUMMARY:")
        brief_summary = summaries.get("brief_summary", "N/A")
        urgency = summaries.get("urgency_level", "routine")
        print(f"  {brief_summary[:100]}...")
        print(f"  Urgency: {urgency.upper()}")
        key_findings_count = len(
            summaries.get("detailed_summary", {}).get("key_findings", [])
        )
        print(f"  Key Findings: {key_findings_count}")

        print("\n[GRAPH] CLINICAL RELATIONSHIPS:")
        print(f"  Total: {relationships.get('total_count', 0)}")
        print(f"  By Type: {relationships.get('summary', {}).get('by_type', {})}")
        print(f"\n{'='*60}\n")

        # Step 4: Save to Database
        print("💾 SAVING TO DATABASE...")

        document_id = str(document_id_uuid)

        # Create User and Document records first (required for foreign keys)
        try:
            print(f"✓ User: {user.id}")

            # Create document record
            doc_date = doc_metadata.get("document_date")
            if doc_date:
                try:
                    doc_date = (
                        datetime.strptime(doc_date, "%Y-%m-%d")
                        if isinstance(doc_date, str)
                        else doc_date
                    )
                except:
                    doc_date = None

            document = db_service.create_document(
                document_id=document_id,
                user_id=user_id,
                filename=upload_result["file_path"],
                original_name=file.filename,
                mime_type=file.content_type or "application/octet-stream",
                file_size=file_size,
                file_path=upload_result["file_path"],
                document_type=doc_type,
                document_date=doc_date,
            )
            print(f"✓ Document: {document.id}")

            # Now save agent results to database
            persistence_service = AgentPersistenceService(db)
            processing_result = persistence_service.save_agent_results(
                document_id=document_id,
                user_id=user_id,
                agent_results=agent_results,
            )
            print(f"✓ Agent Results: {processing_result.id}")
            print(
                f"  - Clinical Records: {len(clinical_data.get('conditions', []))} conditions, "
                f"{len(clinical_data.get('medications', []))} medications, "
                f"{len(clinical_data.get('lab_results', []))} labs"
            )

            # Update document extraction status to completed
            status = "completed"
            db_service.update_document_extraction(
                document_id=document_id,
                status=status,
                extracted_data=agent_results,
            )
            print(f"✓ Document status updated to '{status}'")

            # Step 5: Create vector embeddings for RAG using search-optimized summaries
            print("\n🔍 CREATING SMART VECTOR EMBEDDINGS FOR RAG...")
            try:
                from src.services.embeddings_service import embeddings_service

                # Create document embeddings using Agent 3's search-optimized summaries
                doc_embeddings = embeddings_service.create_document_embeddings(
                    db=db,
                    document=document,
                    summaries=agent_results.get("summaries", {}),
                    clinical_data=agent_results.get("clinical_data", {}),
                )
                print(f"✓ Created {len(doc_embeddings)} smart document embeddings")

                # Create timeline event embeddings with search summaries from Agent 3
                from src.models import TimelineEvent

                timeline_events = (
                    db.query(TimelineEvent)
                    .filter(
                        TimelineEvent.document_id == document_id,
                        TimelineEvent.deleted_at.is_(None),
                    )
                    .all()
                )

                # Get temporal_events from Agent 3 to match with timeline events
                temporal_events = (
                    agent_results.get("summaries", {})
                    .get("agent_context", {})
                    .get("temporal_events", [])
                )

                for event in timeline_events:
                    # Find matching temporal_event with search_summary
                    search_summary = None
                    for temp_event in temporal_events:
                        if (
                            temp_event.get("event_title") == event.event_title
                            or temp_event.get("event_type") == event.event_type
                        ):
                            search_summary = temp_event.get("search_summary")
                            break

                    embeddings_service.create_timeline_event_embedding(
                        db=db, event=event, search_summary=search_summary
                    )
                print(f"✓ Created {len(timeline_events)} timeline event embeddings")

                # Create clinical entity embeddings (conditions, medications, labs, procedures)
                # These power entity-level RAG lookups in the Ask AI chat feature.
                from src.models.clinical_data import (
                    ClinicalCondition as ClinicalConditionModel,
                    ClinicalMedication as ClinicalMedicationModel,
                    ClinicalLabResult as ClinicalLabResultModel,
                    ClinicalProcedure as ClinicalProcedureModel,
                )

                entity_count = 0

                # Conditions
                conditions_db = (
                    db.query(ClinicalConditionModel)
                    .filter(
                        ClinicalConditionModel.document_id == document_id,
                        ClinicalConditionModel.deleted_at.is_(None),
                    )
                    .all()
                )
                for cond in conditions_db:
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
                                "diagnosed_date": (
                                    str(cond.diagnosed_date)
                                    if cond.diagnosed_date
                                    else None
                                ),
                            },
                        )
                        entity_count += 1
                    except Exception:
                        pass

                # Medications
                medications_db = (
                    db.query(ClinicalMedicationModel)
                    .filter(
                        ClinicalMedicationModel.document_id == document_id,
                        ClinicalMedicationModel.deleted_at.is_(None),
                    )
                    .all()
                )
                for med in medications_db:
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
                                "start_date": (
                                    str(med.start_date) if med.start_date else None
                                ),
                                "status": "active" if med.is_active else "stopped",
                                "instructions": med.notes,
                            },
                        )
                        entity_count += 1
                    except Exception:
                        pass

                # Lab results
                labs_db = (
                    db.query(ClinicalLabResultModel)
                    .filter(
                        ClinicalLabResultModel.document_id == document_id,
                        ClinicalLabResultModel.deleted_at.is_(None),
                    )
                    .all()
                )
                for lab in labs_db:
                    try:
                        embeddings_service.create_clinical_entity_embedding(
                            db=db,
                            user_id=user_id,
                            entity_type="lab_result",
                            entity_id=lab.id,
                            entity_name=lab.test_name,
                            entity_data={
                                "loinc_code": lab.loinc_code,
                                "value": lab.value,
                                "unit": lab.unit,
                                "reference_range": lab.reference_range,
                                "is_abnormal": lab.is_abnormal,
                                "test_date": (
                                    str(lab.test_date) if lab.test_date else None
                                ),
                            },
                        )
                        entity_count += 1
                    except Exception:
                        pass

                # Procedures
                procedures_db = (
                    db.query(ClinicalProcedureModel)
                    .filter(
                        ClinicalProcedureModel.document_id == document_id,
                        ClinicalProcedureModel.deleted_at.is_(None),
                    )
                    .all()
                )
                for proc in procedures_db:
                    try:
                        embeddings_service.create_clinical_entity_embedding(
                            db=db,
                            user_id=user_id,
                            entity_type="procedure",
                            entity_id=proc.id,
                            entity_name=proc.procedure_name,
                            entity_data={
                                "cpt_code": proc.cpt_code,
                                "performed_date": (
                                    str(proc.performed_date)
                                    if proc.performed_date
                                    else None
                                ),
                                "provider": proc.provider,
                                "facility": proc.facility,
                                "outcome": proc.outcome,
                            },
                        )
                        entity_count += 1
                    except Exception:
                        pass

                print(f"✓ Created {entity_count} clinical entity embeddings")

            except Exception as embed_error:
                print(
                    f"⚠️  Embeddings creation failed (non-critical): {str(embed_error)}"
                )
                import traceback

                traceback.print_exc()
                # Don't fail the request if embeddings fail

        except Exception as db_error:
            print(f"⚠️  Database save failed: {str(db_error)}")
            import traceback

            traceback.print_exc()
            # Don't fail the request if database save fails
            # TODO: Implement proper error handling and retry logic

        print(f"{'='*60}\n")

        # Step 5: Create response with new agent structure
        file_info_response = FileInfo(
            original_filename=file.filename,
            saved_filename=upload_result["file_path"],
            file_size=format_file_size(file_size),
            file_type=file_type,
            upload_timestamp=datetime.now(),
        )

        # Combine agent results from new structure
        detailed_summary = summaries.get("detailed_summary", {})
        combined_data = {
            "text": summaries.get("brief_summary", ""),
            "labels": [doc_type],  # Use validated document type
            "summary": summaries.get("brief_summary", ""),
            "classification": {
                "document_type": doc_type,
                "document_date": doc_metadata.get("document_date"),
                "provider": doc_metadata.get("provider"),
                "facility": doc_metadata.get("facility"),
                "confidence": validation.get("validation", {}).get("quality_score", 0),
            },
            "medical_data": clinical_data,  # Full clinical extraction
            "analysis": {
                "brief_summary": summaries.get("brief_summary", ""),
                "detailed_summary": detailed_summary,
                "urgency_level": summaries.get("urgency_level", "routine"),
                "key_findings": detailed_summary.get("key_findings", []),
                "treatment_plan": detailed_summary.get("treatment_plan", {}),
                "agent_context": summaries.get("agent_context", {}),
            },
            "raw_output": agent_results,
        }

        extracted_data_response = ExtractedData(**combined_data)

        return DocumentUploadResponse(
            success=True,
            message="Document analyzed by 3 specialized AI agents",
            file_info=file_info_response,
            extracted_data=extracted_data_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
