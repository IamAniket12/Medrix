"""
Reset database and add test user.

This script:
1. Deletes all data from all tables
2. Creates a test user (test-user-123)
3. Confirms deletion and creation

Usage:
    python reset_database.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from src.core.database import engine, SessionLocal
from src.models import (
    Base,
    User,
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
    AuditLog,
    SearchTerm,
)


def count_records(db: Session):
    """Count records in all tables."""
    counts = {
        "users": db.query(User).count(),
        "documents": db.query(Document).count(),
        "processing_results": db.query(DocumentProcessingResult).count(),
        "summaries": db.query(DocumentSummary).count(),
        "conditions": db.query(ClinicalCondition).count(),
        "medications": db.query(ClinicalMedication).count(),
        "allergies": db.query(ClinicalAllergy).count(),
        "lab_results": db.query(ClinicalLabResult).count(),
        "vital_signs": db.query(ClinicalVitalSign).count(),
        "procedures": db.query(ClinicalProcedure).count(),
        "immunizations": db.query(ClinicalImmunization).count(),
        "timeline_events": db.query(TimelineEvent).count(),
        "audit_logs": db.query(AuditLog).count(),
        "search_terms": db.query(SearchTerm).count(),
    }
    return counts


def print_counts(title: str, counts: dict):
    """Print table counts."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")
    total = 0
    for table, count in counts.items():
        print(f"  {table:<25} {count:>6} records")
        total += count
    print(f"{'=' * 60}")
    print(f"  {'TOTAL':<25} {total:>6} records")
    print(f"{'=' * 60}\n")


def reset_database():
    """Reset all data and add test user."""
    db = SessionLocal()

    try:
        print("\n🚀 Starting database reset...\n")

        # Count before deletion
        print("📊 Current database state:")
        before_counts = count_records(db)
        print_counts("BEFORE RESET", before_counts)

        # Confirm deletion
        if before_counts["users"] > 0 or before_counts["documents"] > 0:
            response = input("⚠️  This will delete ALL data. Continue? (yes/no): ")
            if response.lower() != "yes":
                print("❌ Reset cancelled.")
                return

        print("🗑️  Deleting all data...")

        # Delete in correct order (respecting foreign keys)
        # Start with child tables, then parent tables

        # 1. Clinical data and timeline
        db.query(SearchTerm).delete()
        db.query(AuditLog).delete()
        db.query(TimelineEvent).delete()
        db.query(ClinicalImmunization).delete()
        db.query(ClinicalProcedure).delete()
        db.query(ClinicalVitalSign).delete()
        db.query(ClinicalLabResult).delete()
        db.query(ClinicalAllergy).delete()
        db.query(ClinicalMedication).delete()
        db.query(ClinicalCondition).delete()

        # 2. Document processing
        db.query(DocumentSummary).delete()
        db.query(DocumentProcessingResult).delete()

        # 3. Documents
        db.query(Document).delete()

        # 4. Users (last, because of cascade)
        db.query(User).delete()

        db.commit()
        print("✅ All data deleted successfully!\n")

        # Count after deletion
        after_counts = count_records(db)
        print_counts("AFTER DELETION", after_counts)

        # Create test user
        print("👤 Creating test user...")
        test_user = User(id="test-user-123", email="test@medrix.com", name="Test User")
        db.add(test_user)
        db.commit()

        print("✅ Test user created successfully!")
        print(f"   User ID: {test_user.id}")
        print(f"   Email: {test_user.email}")
        print(f"   Name: {test_user.name}\n")

        # Final count
        final_counts = count_records(db)
        print_counts("FINAL STATE", final_counts)

        print("🎉 Database reset complete!")
        print("\n📝 Next steps:")
        print("   1. Upload a medical document via the API or frontend")
        print("   2. Wait for AI processing (~30 seconds)")
        print("   3. Visit http://localhost:3000/timeline to see your timeline")
        print(
            "   4. Test AI insights: curl http://localhost:8000/api/v1/clinical/timeline/test-user-123/insights"
        )
        print("\n")

    except Exception as e:
        print(f"\n❌ Error during reset: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_database()
