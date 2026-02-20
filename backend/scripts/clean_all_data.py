#!/usr/bin/env python3
"""
Clean ALL data from Medrix database tables.
WARNING: This will permanently delete ALL data!
Use only in development/testing.
"""

import sys
import os

# Add parent directory to path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from src.core.database import SessionLocal, engine
from src.models import (
    Document,
    DocumentProcessingResult,
    DocumentSummary,
    DocumentEmbedding,
    TimelineEvent,
    TimelineEventEmbedding,
    ClinicalEntityEmbedding,
    ClinicalCondition,
    ClinicalMedication,
    ClinicalAllergy,
    ClinicalLabResult,
    ClinicalVitalSign,
    ClinicalProcedure,
    ClinicalImmunization,
    AuditLog,
    SearchTerm,
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def confirm_deletion():
    """Ask user to confirm deletion."""
    print("\n" + "=" * 70)
    print("⚠️  WARNING: DATABASE CLEANUP")
    print("=" * 70)
    print("\nThis will permanently delete ALL data from the following tables:")
    print("  - documents")
    print("  - document_processing_results")
    print("  - document_summaries")
    print("  - document_embeddings")
    print("  - timeline_events")
    print("  - timeline_event_embeddings")
    print("  - clinical_entity_embeddings")
    print("  - clinical_conditions")
    print("  - clinical_medications")
    print("  - clinical_allergies")
    print("  - clinical_lab_results")
    print("  - clinical_vital_signs")
    print("  - clinical_procedures")
    print("  - clinical_immunizations")
    print("  - audit_logs")
    print("  - search_terms")
    print("\n⚠️  NOTE: User table will NOT be deleted")
    print("\n" + "=" * 70)

    response = input("\nType 'DELETE ALL DATA' to confirm: ")

    if response != "DELETE ALL DATA":
        print("\n❌ Cleanup cancelled.")
        return False

    # Double confirmation
    response2 = input("\nAre you ABSOLUTELY sure? Type 'YES' to proceed: ")

    if response2 != "YES":
        print("\n❌ Cleanup cancelled.")
        return False

    return True


def clean_all_data():
    """Delete all data from all tables."""

    if not confirm_deletion():
        return

    db = SessionLocal()

    try:
        print("\n🧹 Starting database cleanup...")
        print("⚠️  Using raw SQL to bypass soft-delete filters and delete ALL data...\n")

        # Use raw SQL to delete ALL records (including soft-deleted ones)
        # Order matters due to foreign key constraints

        print("1. Deleting embeddings...")
        result = db.execute(text("DELETE FROM clinical_entity_embeddings"))
        print(f"   ✓ Deleted {result.rowcount} clinical entity embeddings")

        result = db.execute(text("DELETE FROM timeline_event_embeddings"))
        print(f"   ✓ Deleted {result.rowcount} timeline event embeddings")

        result = db.execute(text("DELETE FROM document_embeddings"))
        print(f"   ✓ Deleted {result.rowcount} document embeddings")

        print("\n2. Deleting audit & search data...")
        result = db.execute(text("DELETE FROM audit_logs"))
        print(f"   ✓ Deleted {result.rowcount} audit logs")

        result = db.execute(text("DELETE FROM search_terms"))
        print(f"   ✓ Deleted {result.rowcount} search terms")

        print("\n3. Deleting clinical data...")
        result = db.execute(text("DELETE FROM clinical_immunizations"))
        print(f"   ✓ Deleted {result.rowcount} immunizations")

        result = db.execute(text("DELETE FROM clinical_procedures"))
        print(f"   ✓ Deleted {result.rowcount} procedures")

        result = db.execute(text("DELETE FROM clinical_vital_signs"))
        print(f"   ✓ Deleted {result.rowcount} vital signs")

        result = db.execute(text("DELETE FROM clinical_lab_results"))
        print(f"   ✓ Deleted {result.rowcount} lab results")

        result = db.execute(text("DELETE FROM clinical_allergies"))
        print(f"   ✓ Deleted {result.rowcount} allergies")

        result = db.execute(text("DELETE FROM clinical_medications"))
        print(f"   ✓ Deleted {result.rowcount} medications")

        result = db.execute(text("DELETE FROM clinical_conditions"))
        print(f"   ✓ Deleted {result.rowcount} conditions")

        print("\n4. Deleting timeline events...")
        result = db.execute(text("DELETE FROM timeline_events"))
        print(f"   ✓ Deleted {result.rowcount} timeline events")

        print("\n5. Deleting document processing data...")
        result = db.execute(text("DELETE FROM document_summaries"))
        print(f"   ✓ Deleted {result.rowcount} document summaries")

        result = db.execute(text("DELETE FROM document_processing_results"))
        print(f"   ✓ Deleted {result.rowcount} document processing results")

        print("\n6. Deleting documents...")
        result = db.execute(text("DELETE FROM documents"))
        print(f"   ✓ Deleted {result.rowcount} documents")

        # Commit all deletions
        db.commit()

        print("\n" + "=" * 70)
        print("✅ DATABASE CLEANUP COMPLETE")
        print("=" * 70)
        print("\nAll data has been permanently deleted (except users).")
        print("The database is now empty and ready for fresh data.\n")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error during cleanup: {e}")
        import traceback

        traceback.print_exc()

    finally:
        db.close()


def reset_sequences():
    """Reset auto-increment sequences (optional)."""
    db = SessionLocal()

    try:
        print("\n7. Resetting ID sequences...")

        # Get all tables with ID columns (except users)
        tables = [
            "documents",
            "document_processing_results",
            "document_summaries",
            "document_embeddings",
            "timeline_events",
            "timeline_event_embeddings",
            "clinical_entity_embeddings",
            "clinical_conditions",
            "clinical_medications",
            "clinical_allergies",
            "clinical_lab_results",
            "clinical_vital_signs",
            "clinical_procedures",
            "clinical_immunizations",
            "audit_logs",
            "search_terms",
        ]

        for table in tables:
            try:
                # Reset PostgreSQL sequence
                db.execute(text(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1"))
                print(f"   ✓ Reset {table} ID sequence")
            except Exception as e:
                # Some tables might not have sequences
                pass

        db.commit()
        print("\n✅ ID sequences reset successfully")

    except Exception as e:
        logger.error(f"⚠️  Error resetting sequences: {e}")

    finally:
        db.close()


def main():
    """Main execution."""
    print("\n🗑️  MEDRIX DATABASE CLEANUP SCRIPT")
    print("=" * 70)

    # Clean all data
    clean_all_data()

    # Ask if user wants to reset sequences
    response = input("\nReset ID sequences to start from 1? (y/n): ")
    if response.lower() == "y":
        reset_sequences()

    print("\n✅ Cleanup complete! Database is now empty.\n")


if __name__ == "__main__":
    main()
