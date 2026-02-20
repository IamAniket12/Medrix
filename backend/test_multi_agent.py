#!/usr/bin/env python3
"""Test multi-agent document upload"""

import requests
import json
from PIL import Image, ImageDraw, ImageFont

# Upload endpoint
url = "http://localhost:8000/api/v1/documents/upload"

# Create a medical report as an image instead of text file
print("Creating test medical report image...")

# Create image with medical report text
img = Image.new("RGB", (800, 600), color="white")
draw = ImageDraw.Draw(img)

# Try to use a default font
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
except:
    font = ImageFont.load_default()
    font_bold = ImageFont.load_default()

# Draw the medical report
y_position = 30
draw.text((50, y_position), "MEDICAL REPORT", fill="black", font=font_bold)
y_position += 50

text_lines = [
    "Patient Name: John Doe",
    "Date: 2024-01-15",
    "Doctor: Dr. Sarah Smith",
    "",
    "DIAGNOSIS:",
    "- Type 2 Diabetes Mellitus",
    "- Hypertension",
    "",
    "MEDICATIONS:",
    "- Metformin 500mg twice daily",
    "- Lisinopril 10mg once daily",
    "",
    "LAB RESULTS:",
    "- HbA1c: 7.2%",
    "- Blood Pressure: 142/88 mmHg",
    "- Glucose: 145 mg/dL",
    "",
    "RECOMMENDATIONS:",
    "Continue current medications.",
    "Follow-up in 3 months.",
]

for line in text_lines:
    draw.text((50, y_position), line, fill="black", font=font)
    y_position += 25

# Save the image
test_file_path = "/tmp/test_medical_report.jpg"
img.save(test_file_path)

# Upload the file
print("📤 Uploading test medical report...")
print("=" * 60)

with open(test_file_path, "rb") as f:
    files = {"file": ("test_medical_report.jpg", f, "image/jpeg")}
    response = requests.post(url, files=files)

print(f"Status Code: {response.status_code}")
print(f"\n📋 Response:")
print("=" * 60)

if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))

    # Extract and display agent results
    print("\n" + "=" * 60)
    print("🤖 MULTI-AGENT ANALYSIS RESULTS")
    print("=" * 60)

    # Classification Agent
    if "classification" in result:
        print("\n📊 CLASSIFICATION AGENT:")
        print(
            f"  Document Type: {result['classification'].get('document_type', 'N/A')}"
        )
        print(f"  Confidence: {result['classification'].get('confidence', 'N/A')}")

    # Extraction Agent
    if "medical_data" in result:
        print("\n🔍 EXTRACTION AGENT:")
        md = result["medical_data"]
        print(f"  Conditions: {', '.join(md.get('conditions', []))}")
        print(f"  Medications: {', '.join(md.get('medications', []))}")
        print(f"  Allergies: {', '.join(md.get('allergies', []))}")
        print(f"  Tests: {len(md.get('test_results', []))} tests found")

    # Summary Agent
    if "analysis" in result:
        print("\n📝 SUMMARY AGENT:")
        analysis = result["analysis"]
        print(f"  Summary: {analysis.get('summary', 'N/A')}")
        print(f"  Urgency: {analysis.get('urgency_level', 'N/A')}")
        print(f"  Key Findings: {', '.join(analysis.get('key_findings', []))}")

    print("\n" + "=" * 60)
    print("✅ Multi-agent processing complete!")
else:
    print(f"❌ Error: {response.text}")
