"""Verify database persistence."""

from src.core.database import SessionLocal
from src.models import (
    DocumentProcessingResult,
    ClinicalCondition,
    ClinicalMedication,
    ClinicalLabResult,
    TimelineEvent,
    SearchTerm,
)

db = SessionLocal()

# Count records
processing_results = db.query(DocumentProcessingResult).count()
conditions = db.query(ClinicalCondition).count()
medications = db.query(ClinicalMedication).count()
lab_results = db.query(ClinicalLabResult).count()
timeline_events = db.query(TimelineEvent).count()
search_terms = db.query(SearchTerm).count()

print("\n" + "=" * 60)
print("📊 DATABASE PERSISTENCE VERIFICATION")
print("=" * 60)
print(f"\n📁 Record Counts:")
print(f"  Processing Results: {processing_results}")
print(f"  Conditions: {conditions}")
print(f"  Medications: {medications}")
print(f"  Lab Results: {lab_results}")
print(f"  Timeline Events: {timeline_events}")
print(f"  Search Terms: {search_terms}")

# Show latest processing result
latest = (
    db.query(DocumentProcessingResult)
    .order_by(DocumentProcessingResult.created_at.desc())
    .first()
)

if latest:
    print(f"\n✅ Latest Document Processing:")
    print(f"  Document ID: {latest.document_id}")
    print(f"  Status: {latest.processing_status}")
    print(f"  Valid: {latest.is_valid}")
    print(f"  Quality Score: {latest.quality_score}")
    print(f"  Urgency: {latest.urgency_level}")
    print(f"  Brief Summary: {latest.brief_summary[:100]}...")

    # Show related clinical data
    doc_id = latest.document_id
    doc_conditions = db.query(ClinicalCondition).filter_by(document_id=doc_id).all()
    doc_medications = db.query(ClinicalMedication).filter_by(document_id=doc_id).all()
    doc_labs = db.query(ClinicalLabResult).filter_by(document_id=doc_id).all()

    print(f"\n📋 Clinical Data for this Document:")
    print(f"  Conditions: {len(doc_conditions)}")
    for cond in doc_conditions:
        print(f"    - {cond.name} ({cond.status})")

    print(f"  Medications: {len(doc_medications)}")
    for med in doc_medications:
        print(f"    - {med.name} {med.dosage} {med.frequency}")

    print(f"  Lab Results: {len(doc_labs)}")
    for lab in doc_labs:
        print(
            f"    - {lab.test_name}: {lab.value} {lab.unit} (Abnormal: {lab.is_abnormal})"
        )

    print(f"\n{'='*60}\n")
    print("✅ Database persistence working correctly!")
else:
    print("\n⚠️  No processing results found in database")

db.close()
