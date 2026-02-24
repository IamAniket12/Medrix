"""
Script to delete all records for ananya_user_001 from all tables EXCEPT the users table.
This keeps the user account but removes all associated data.
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.database import SessionLocal
from src.models.user import User
from src.models.document import Document
from src.models.document_processing import DocumentProcessingResult, DocumentSummary
from src.models.embeddings import (
    DocumentEmbedding,
    TimelineEventEmbedding,
    ClinicalEntityEmbedding,
)
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
from src.models.medical_id import MedicalIDCard, TemporaryMedicalSummary


def delete_all_data_for_ananya():
    """Delete all data for ananya_user_001 except the user record itself"""
    db = SessionLocal()

    try:
        user_id = "ananya_user_001"

        print(f"\n{'='*60}")
        print(f"🗑️  DELETING ALL DATA FOR ANANYA (keeping user account)")
        print(f"{'='*60}\n")

        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ User {user_id} not found!")
            return

        print(f"✓ Found user: {user.name} ({user.email})\n")

        # Count all records before deletion
        print(f"📊 Records to delete:\n")

        # Documents and related data
        documents_count = db.query(Document).filter(Document.user_id == user_id).count()
        print(f"   📄 Documents: {documents_count}")

        embeddings_count = (
            db.query(DocumentEmbedding)
            .filter(DocumentEmbedding.user_id == user_id)
            .count()
        )
        print(f"   🔢 Document Embeddings: {embeddings_count}")

        # Get all document IDs for this user
        document_ids = [
            doc.id for doc in db.query(Document).filter(Document.user_id == user_id)
        ]

        if document_ids:
            processing_count = (
                db.query(DocumentProcessingResult)
                .filter(DocumentProcessingResult.document_id.in_(document_ids))
                .count()
            )
            summaries_count = (
                db.query(DocumentSummary)
                .filter(DocumentSummary.document_id.in_(document_ids))
                .count()
            )
        else:
            processing_count = 0
            summaries_count = 0

        print(f"   📋 Processing Results: {processing_count}")
        print(f"   📝 Document Summaries: {summaries_count}")

        # Clinical data
        conditions_count = (
            db.query(ClinicalCondition)
            .filter(ClinicalCondition.user_id == user_id)
            .count()
        )
        print(f"   🏥 Conditions: {conditions_count}")

        medications_count = (
            db.query(ClinicalMedication)
            .filter(ClinicalMedication.user_id == user_id)
            .count()
        )
        print(f"   💊 Medications: {medications_count}")

        allergies_count = (
            db.query(ClinicalAllergy).filter(ClinicalAllergy.user_id == user_id).count()
        )
        print(f"   ⚠️  Allergies: {allergies_count}")

        labs_count = (
            db.query(ClinicalLabResult)
            .filter(ClinicalLabResult.user_id == user_id)
            .count()
        )
        print(f"   🧪 Lab Results: {labs_count}")

        vitals_count = (
            db.query(ClinicalVitalSign)
            .filter(ClinicalVitalSign.user_id == user_id)
            .count()
        )
        print(f"   💓 Vital Signs: {vitals_count}")

        procedures_count = (
            db.query(ClinicalProcedure)
            .filter(ClinicalProcedure.user_id == user_id)
            .count()
        )
        print(f"   🔧 Procedures: {procedures_count}")

        immunizations_count = (
            db.query(ClinicalImmunization)
            .filter(ClinicalImmunization.user_id == user_id)
            .count()
        )
        print(f"   💉 Immunizations: {immunizations_count}")

        # Timeline
        timeline_count = (
            db.query(TimelineEvent).filter(TimelineEvent.user_id == user_id).count()
        )
        print(f"   📅 Timeline Events: {timeline_count}")

        timeline_embeddings_count = (
            db.query(TimelineEventEmbedding)
            .filter(TimelineEventEmbedding.user_id == user_id)
            .count()
        )
        print(f"   🔢 Timeline Embeddings: {timeline_embeddings_count}")

        # Clinical entity embeddings
        entity_embeddings_count = (
            db.query(ClinicalEntityEmbedding)
            .filter(ClinicalEntityEmbedding.user_id == user_id)
            .count()
        )
        print(f"   🔢 Entity Embeddings: {entity_embeddings_count}")

        # Medical ID
        medical_id_count = (
            db.query(MedicalIDCard).filter(MedicalIDCard.user_id == user_id).count()
        )
        print(f"   🆔 Medical ID Cards: {medical_id_count}")

        temp_summary_count = (
            db.query(TemporaryMedicalSummary)
            .filter(TemporaryMedicalSummary.user_id == user_id)
            .count()
        )
        print(f"   📋 Temporary Summaries: {temp_summary_count}")

        total_records = (
            documents_count
            + embeddings_count
            + processing_count
            + summaries_count
            + conditions_count
            + medications_count
            + allergies_count
            + labs_count
            + vitals_count
            + procedures_count
            + immunizations_count
            + timeline_count
            + timeline_embeddings_count
            + entity_embeddings_count
            + medical_id_count
            + temp_summary_count
        )

        print(f"\n   💥 TOTAL RECORDS: {total_records}")

        if total_records == 0:
            print(f"\n✓ No data to delete. User account is clean!")
            return

        # Confirm deletion
        print(f"\n{'='*60}")
        response = input(
            f"⚠️  Delete {total_records} records for {user.name}? (yes/no): "
        )
        if response.lower() != "yes":
            print("❌ Operation cancelled.")
            return

        print(f"\n🗑️  Starting deletion...\n")

        # Delete in correct order (respecting foreign keys)
        # Start with dependent records first

        # 1. Delete embeddings (no dependencies)
        if embeddings_count > 0:
            deleted = (
                db.query(DocumentEmbedding)
                .filter(DocumentEmbedding.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} document embeddings")

        if timeline_embeddings_count > 0:
            deleted = (
                db.query(TimelineEventEmbedding)
                .filter(TimelineEventEmbedding.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} timeline embeddings")

        if entity_embeddings_count > 0:
            deleted = (
                db.query(ClinicalEntityEmbedding)
                .filter(ClinicalEntityEmbedding.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} entity embeddings")

        # 2. Delete document-dependent records
        if document_ids:
            if processing_count > 0:
                deleted = (
                    db.query(DocumentProcessingResult)
                    .filter(DocumentProcessingResult.document_id.in_(document_ids))
                    .delete(synchronize_session=False)
                )
                print(f"   ✓ Deleted {deleted} processing results")

            if summaries_count > 0:
                deleted = (
                    db.query(DocumentSummary)
                    .filter(DocumentSummary.document_id.in_(document_ids))
                    .delete(synchronize_session=False)
                )
                print(f"   ✓ Deleted {deleted} document summaries")

        # 3. Delete clinical data (may reference documents)
        if conditions_count > 0:
            deleted = (
                db.query(ClinicalCondition)
                .filter(ClinicalCondition.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} conditions")

        if medications_count > 0:
            deleted = (
                db.query(ClinicalMedication)
                .filter(ClinicalMedication.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} medications")

        if allergies_count > 0:
            deleted = (
                db.query(ClinicalAllergy)
                .filter(ClinicalAllergy.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} allergies")

        if labs_count > 0:
            deleted = (
                db.query(ClinicalLabResult)
                .filter(ClinicalLabResult.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} lab results")

        if vitals_count > 0:
            deleted = (
                db.query(ClinicalVitalSign)
                .filter(ClinicalVitalSign.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} vital signs")

        if procedures_count > 0:
            deleted = (
                db.query(ClinicalProcedure)
                .filter(ClinicalProcedure.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} procedures")

        if immunizations_count > 0:
            deleted = (
                db.query(ClinicalImmunization)
                .filter(ClinicalImmunization.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} immunizations")

        # 4. Delete timeline events
        if timeline_count > 0:
            deleted = (
                db.query(TimelineEvent)
                .filter(TimelineEvent.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} timeline events")

        # 5. Delete medical ID cards
        if medical_id_count > 0:
            deleted = (
                db.query(MedicalIDCard)
                .filter(MedicalIDCard.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} medical ID cards")

        if temp_summary_count > 0:
            deleted = (
                db.query(TemporaryMedicalSummary)
                .filter(TemporaryMedicalSummary.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} temporary summaries")

        # 6. Finally delete documents (parent of many relations)
        if documents_count > 0:
            deleted = (
                db.query(Document)
                .filter(Document.user_id == user_id)
                .delete(synchronize_session=False)
            )
            print(f"   ✓ Deleted {deleted} documents")

        # Commit all deletions
        db.commit()

        print(f"\n{'='*60}")
        print(f"✅ CLEANUP COMPLETE")
        print(f"{'='*60}\n")
        print(f"✓ Deleted {total_records} records for {user.name}")
        print(f"✓ User account {user_id} is retained and clean")
        print(f"✓ User can now upload fresh documents\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    delete_all_data_for_ananya()
