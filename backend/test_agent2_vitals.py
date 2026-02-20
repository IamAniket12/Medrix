"""
Test Agent 2 improved prompt - Focus on vital signs extraction
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.agent_orchestrator import MedicalDocumentAgentOrchestrator
from src.core.config import settings


async def test_vitals_extraction():
    """Test vital signs extraction with the improved Agent 2 prompt."""

    # Test with a sample image (you'll need to provide the path)
    test_image_path = input("Enter path to test medical document image: ").strip()

    if not Path(test_image_path).exists():
        print(f"❌ File not found: {test_image_path}")
        return

    # Read image
    with open(test_image_path, "rb") as f:
        image_bytes = f.read()

    # Initialize orchestrator
    orchestrator = MedicalDocumentAgentOrchestrator(settings)

    # Create test state
    state = {
        "image_bytes": image_bytes,
        "filename": Path(test_image_path).name,
        "file_type": "image",
        "patient_context": {"active_medications": [], "active_conditions": []},
        "is_valid": True,
        "should_continue": True,
        "errors": [],
    }

    print("\n" + "=" * 70)
    print("🧪 TESTING AGENT 2 - CLINICAL EXTRACTOR (IMPROVED PROMPT)")
    print("=" * 70)

    # Run Agent 2
    result = await orchestrator._clinical_extractor(state)

    clinical_data = result.get("clinical_data", {})

    print("\n📊 EXTRACTION RESULTS:")
    print("=" * 70)

    # Display all categories
    categories = [
        ("CONDITIONS", "conditions"),
        ("MEDICATIONS", "medications"),
        ("ALLERGIES", "allergies"),
        ("LAB RESULTS", "lab_results"),
        ("VITAL SIGNS", "vital_signs"),
        ("PROCEDURES", "procedures"),
        ("IMMUNIZATIONS", "immunizations"),
    ]

    for category_name, key in categories:
        items = clinical_data.get(key, [])
        print(f"\n{category_name}: {len(items)} items")
        if items:
            for i, item in enumerate(items, 1):
                print(f"  {i}. {item}")

    # Special focus on vital signs
    vital_signs = clinical_data.get("vital_signs", [])
    print("\n" + "=" * 70)
    print("🎯 VITAL SIGNS DETAILED ANALYSIS:")
    print("=" * 70)

    if vital_signs:
        vital_types = {}
        for vs in vital_signs:
            vs_type = vs.get("type", "unknown")
            vital_types[vs_type] = vs

        print(f"\n✅ Extracted {len(vital_signs)} vital signs:")
        for vs_type, data in vital_types.items():
            if vs_type == "blood_pressure":
                print(
                    f"  • Blood Pressure: {data.get('systolic')}/{data.get('diastolic')} {data.get('unit')}"
                )
            else:
                print(
                    f"  • {vs_type.replace('_', ' ').title()}: {data.get('value')} {data.get('unit')}"
                )

        # Check completeness
        expected_vitals = [
            "blood_pressure",
            "heart_rate",
            "temperature",
            "respiratory_rate",
            "oxygen_saturation",
            "weight",
            "height",
            "bmi",
        ]
        missing_vitals = [v for v in expected_vitals if v not in vital_types]

        if missing_vitals:
            print(f"\n⚠️  Potentially missing vital signs: {', '.join(missing_vitals)}")
            print("   (These may not be present in the document)")
    else:
        print("\n❌ NO VITAL SIGNS EXTRACTED!")
        print("   Check if the document contains vital signs in the following formats:")
        print("   • BP: 120/80, Blood Pressure: 140/90 mmHg")
        print("   • HR: 72 bpm, Pulse: 88")
        print("   • Temp: 98.6°F, Temperature: 37°C")
        print("   • RR: 16, Resp: 18 breaths/min")
        print("   • O2: 98%, SpO2: 97%")
        print("   • Weight: 180 lbs, Wt: 82 kg")
        print("   • Height: 5'10\", Ht: 178 cm")

    print("\n" + "=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_vitals_extraction())
