"""
Script to delete sarah_1.jpg document from demo_user_001 (Rajesh) from all tables.
This removes the incorrectly uploaded document and all its related data.
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from src.core.database import SessionLocal
from src.models.document import Document
from src.models.document_processing import DocumentProcessingResult, DocumentSummary
from src.models.embeddings import DocumentEmbedding
from src.models.clinical_data import (
    ClinicalCondition,
    ClinicalMedication,
    ClinicalLabResult,
    ClinicalProcedure,
    ClinicalAllergy,
    ClinicalImmunization,
    ClinicalVitalSign,
)
from src.models.timeline import TimelineEvent


def delete_sarah_1_from_rajesh():
    """Delete sarah_1.jpg document from demo_user_001"""
    db = SessionLocal()

    try:
        # Specific document ID to delete
        document_id = "11609e37-44b3-4863-9f20-06f922838580"

        print(f"\n{'='*60}")
        print(f"🗑️  DELETING SARAH_1 DOCUMENT FROM RAJESH (demo_user_001)")
        print(f"{'='*60}\n")

        # Find the document by ID
        doc = db.query(Document).filter(Document.id == document_id).first()

        if not doc:
            print(f"❌ Document not found with ID: {document_id}")
            return

        print(f"Found document to delete:\n")
        print(f"📄 Document ID: {doc.id}")
        print(f"   User ID: {doc.user_id}")
        print(f"   Filename: {doc.original_name}")
        print(f"   Uploaded: {doc.uploaded_at}")
        print(f"   Type: {doc.document_type}")
        print()

        # Count related records before deletion
        embeddings_count = (
            db.query(DocumentEmbedding)
            .filter(DocumentEmbedding.document_id == doc.id)
            .count()
        )

        processing_count = (
            db.query(DocumentProcessingResult)
            .filter(DocumentProcessingResult.document_id == doc.id)
            .count()
        )

        summary_count = (
            db.query(DocumentSummary)
            .filter(DocumentSummary.document_id == doc.id)
            .count()
        )

        conditions_count = (
            db.query(ClinicalCondition)
            .filter(ClinicalCondition.document_id == doc.id)
            .count()
        )

        medications_count = (
            db.query(ClinicalMedication)
            .filter(ClinicalMedication.document_id == doc.id)
            .count()
        )

        labs_count = (
            db.query(ClinicalLabResult)
            .filter(ClinicalLabResult.document_id == doc.id)
            .count()
        )

        procedures_count = (
            db.query(ClinicalProcedure)
            .filter(ClinicalProcedure.document_id == doc.id)
            .count()
        )

        allergies_count = (
            db.query(ClinicalAllergy)
            .filter(ClinicalAllergy.document_id == doc.id)
            .count()
        )

        immunizations_count = (
            db.query(ClinicalImmunization)
            .filter(ClinicalImmunization.document_id == doc.id)
            .count()
        )

        vitals_count = (
            db.query(ClinicalVitalSign)
            .filter(ClinicalVitalSign.document_id == doc.id)
            .count()
        )

        timeline_count = (
            db.query(TimelineEvent).filter(TimelineEvent.document_id == doc.id).count()
        )

        print(f"   Related records:")
        print(f"   - Embeddings: {embeddings_count}")
        print(f"   - Processing Results: {processing_count}")
        print(f"   - Summaries: {summary_count}")
        print(f"   - Conditions: {conditions_count}")
        print(f"   - Medications: {medications_count}")
        print(f"   - Lab Tests: {labs_count}")
        print(f"   - Procedures: {procedures_count}")
        print(f"   - Allergies: {allergies_count}")
        print(f"   - Immunizations: {immunizations_count}")
        print(f"   - Vitals: {vitals_count}")
        print(f"   - Timeline Events: {timeline_count}")
        print()

        # Delete the document (cascade should handle related records)
        print(f"🗑️  Deleting document {doc.id}...")
        db.delete(doc)
        db.commit()
        print(f"✓ Document deleted successfully!")
        print()

        print(f"\n{'='*60}")
        print(f"✅ CLEANUP COMPLETE")
        print(f"{'='*60}\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    delete_sarah_1_from_rajesh()
