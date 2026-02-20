#!/usr/bin/env python3
"""
Generate realistic medical document PDFs for testing the 5-agent system.
Creates a comprehensive patient history with multiple document types.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import os
from datetime import datetime, timedelta

OUTPUT_DIR = "test_data/patient_1_general"


def create_header(elements, styles, clinic_name, doc_type, date):
    """Create document header."""
    # Clinic name
    header_style = ParagraphStyle(
        "CustomHeader",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#1a5490"),
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    elements.append(Paragraph(clinic_name, header_style))

    # Document type
    doc_type_style = ParagraphStyle(
        "DocType",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#333333"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    elements.append(Paragraph(doc_type, doc_type_style))

    # Date
    date_style = ParagraphStyle(
        "DateStyle",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_RIGHT,
        spaceAfter=20,
    )
    elements.append(Paragraph(f"Date: {date}", date_style))
    elements.append(Spacer(1, 0.2 * inch))


def generate_initial_consultation():
    """Generate initial consultation PDF."""
    filename = f"{OUTPUT_DIR}/01_initial_consultation_2024_01_15.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    create_header(
        elements,
        styles,
        "City General Hospital",
        "INITIAL CONSULTATION REPORT",
        "January 15, 2024",
    )

    # Patient Info
    patient_data = [
        ["Patient Name:", "John Anderson", "DOB:", "05/12/1978 (45 years)"],
        ["MRN:", "MRN-2024-001", "Gender:", "Male"],
        ["Phone:", "(555) 123-4567", "Email:", "john.anderson@email.com"],
    ]

    t = Table(patient_data, colWidths=[1.2 * inch, 2 * inch, 0.8 * inch, 2 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f4f8")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#e8f4f8")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 0.3 * inch))

    # Chief Complaint
    elements.append(Paragraph("<b>Chief Complaint:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "Patient presents with persistent fatigue, increased thirst, and frequent urination over the past 2 months. Also reports blurred vision occasionally.",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    # Medical History
    elements.append(Paragraph("<b>Medical History:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "• <b>Hypertension</b> - diagnosed 2020, currently managed<br/>"
            "• <b>Family history</b> of Type 2 Diabetes (father, grandfather)<br/>"
            "• No known drug allergies<br/>"
            "• Non-smoker, occasional alcohol use",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    # Vital Signs
    elements.append(Paragraph("<b>Vital Signs:</b>", styles["Heading3"]))
    vitals_data = [
        ["Blood Pressure:", "145/92 mmHg", "Heart Rate:", "78 bpm"],
        ["Temperature:", "98.6°F (37°C)", "Weight:", "192 lbs (87 kg)"],
        ["Height:", "5'10\" (178 cm)", "BMI:", "27.5 (Overweight)"],
    ]
    t2 = Table(vitals_data, colWidths=[1.5 * inch, 1.8 * inch, 1.2 * inch, 1.5 * inch])
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f0f0f0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(t2)
    elements.append(Spacer(1, 0.2 * inch))

    # Assessment
    elements.append(Paragraph("<b>Assessment:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "1. <b>Suspected Type 2 Diabetes Mellitus (T2DM)</b> - Classic symptoms (polyuria, polydipsia, fatigue)<br/>"
            "2. <b>Hypertension (HTN)</b> - Currently suboptimally controlled<br/>"
            "3. <b>Obesity</b> - BMI 27.5",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    # Plan
    elements.append(Paragraph("<b>Plan:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "1. <b>Laboratory tests ordered:</b><br/>"
            "&nbsp;&nbsp;• Fasting Blood Glucose (FBG)<br/>"
            "&nbsp;&nbsp;• Hemoglobin A1c (HbA1c)<br/>"
            "&nbsp;&nbsp;• Lipid Panel<br/>"
            "&nbsp;&nbsp;• Complete Metabolic Panel (CMP)<br/>"
            "2. <b>Medications:</b><br/>"
            "&nbsp;&nbsp;• Continue Lisinopril 10mg daily for HTN<br/>"
            "3. <b>Lifestyle modifications:</b><br/>"
            "&nbsp;&nbsp;• Dietary counseling - reduce carbohydrate intake<br/>"
            "&nbsp;&nbsp;• Exercise: 30 minutes daily walking<br/>"
            "4. <b>Follow-up:</b> Return in 1 week with lab results",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.3 * inch))

    # Provider signature
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(
        Paragraph(
            "_________________________________<br/>"
            "Dr. Sarah Mitchell, MD<br/>"
            "Internal Medicine<br/>"
            "License: MD-12345",
            styles["Normal"],
        )
    )

    doc.build(elements)
    print(f"✓ Created: {filename}")


def generate_lab_results():
    """Generate lab results PDF."""
    filename = f"{OUTPUT_DIR}/02_lab_results_2024_01_22.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    create_header(
        elements,
        styles,
        "Quest Diagnostics Laboratory",
        "LABORATORY RESULTS",
        "January 22, 2024",
    )

    # Patient Info
    patient_data = [
        ["Patient:", "John Anderson", "DOB:", "05/12/1978"],
        ["MRN:", "MRN-2024-001", "Ordering Physician:", "Dr. Sarah Mitchell"],
        [
            "Collection Date:",
            "01/22/2024 08:15 AM",
            "Report Date:",
            "01/22/2024 14:30 PM",
        ],
    ]

    t = Table(patient_data, colWidths=[1.5 * inch, 2 * inch, 1.5 * inch, 2 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f8ff")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f0f8ff")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 0.3 * inch))

    # Lab Results Table
    elements.append(Paragraph("<b>LABORATORY TEST RESULTS</b>", styles["Heading3"]))
    elements.append(Spacer(1, 0.1 * inch))

    lab_data = [
        ["Test Name", "Result", "Unit", "Reference Range", "Flag"],
        ["Fasting Blood Glucose", "156", "mg/dL", "70-100", "HIGH"],
        ["Hemoglobin A1c (HbA1c)", "7.8", "%", "< 5.7", "HIGH"],
        ["Total Cholesterol", "245", "mg/dL", "< 200", "HIGH"],
        ["LDL Cholesterol", "165", "mg/dL", "< 100", "HIGH"],
        ["HDL Cholesterol", "42", "mg/dL", "> 40", "NORMAL"],
        ["Triglycerides", "190", "mg/dL", "< 150", "HIGH"],
        ["Creatinine", "1.0", "mg/dL", "0.7-1.3", "NORMAL"],
        ["eGFR", "85", "mL/min", "> 60", "NORMAL"],
        ["ALT (SGPT)", "28", "U/L", "7-56", "NORMAL"],
        ["AST (SGOT)", "32", "U/L", "10-40", "NORMAL"],
    ]

    lab_table = Table(
        lab_data, colWidths=[2.2 * inch, 1 * inch, 0.8 * inch, 1.5 * inch, 0.8 * inch]
    )
    lab_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4a90e2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("TEXTCOLOR", (4, 1), (4, 1), colors.red),
                ("TEXTCOLOR", (4, 2), (4, 2), colors.red),
                ("TEXTCOLOR", (4, 3), (4, 3), colors.red),
                ("TEXTCOLOR", (4, 4), (4, 4), colors.red),
                ("TEXTCOLOR", (4, 6), (4, 6), colors.red),
                ("FONTNAME", (4, 1), (4, 6), "Helvetica-Bold"),
            ]
        )
    )
    elements.append(lab_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Interpretation
    elements.append(Paragraph("<b>CLINICAL INTERPRETATION:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "<font color='red'><b>ABNORMAL RESULTS PRESENT</b></font><br/><br/>"
            "Elevated fasting glucose (156 mg/dL) and HbA1c (7.8%) confirm <b>Type 2 Diabetes Mellitus</b>.<br/>"
            "Lipid panel shows dyslipidemia with elevated total cholesterol, LDL, and triglycerides.<br/>"
            "Kidney function (creatinine, eGFR) and liver enzymes are within normal limits.",
            styles["Normal"],
        )
    )

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(
        Paragraph(
            "_________________________________<br/>"
            "Dr. Robert Chen, MD<br/>"
            "Medical Director, Quest Diagnostics<br/>"
            "Electronically signed: 01/22/2024 14:30",
            styles["Normal"],
        )
    )

    doc.build(elements)
    print(f"✓ Created: {filename}")


def generate_diabetes_prescription():
    """Generate diabetes prescription PDF."""
    filename = f"{OUTPUT_DIR}/03_prescription_diabetes_2024_01_23.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    create_header(
        elements,
        styles,
        "City General Hospital - Pharmacy",
        "PRESCRIPTION",
        "January 23, 2024",
    )

    # Patient & Provider Info
    info_data = [
        ["Patient Name:", "John Anderson", "DOB:", "05/12/1978"],
        ["Address:", "123 Main Street, Springfield, IL 62701", "", ""],
        ["Prescriber:", "Dr. Sarah Mitchell, MD", "DEA:", "FM1234563"],
        ["Phone:", "(555) 987-6543", "License:", "MD-12345"],
    ]

    t = Table(info_data, colWidths=[1.2 * inch, 3 * inch, 0.8 * inch, 1.5 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f4f8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 0.4 * inch))

    # Prescription 1
    elements.append(Paragraph("<b>Rx 1:</b>", styles["Heading3"]))
    rx1_data = [
        ["Medication:", "Metformin HCl (Generic for Glucophage)"],
        ["Strength:", "500 mg"],
        ["Form:", "Tablet, Extended Release"],
        ["Directions:", "Take ONE (1) tablet by mouth TWICE daily with meals"],
        ["Quantity:", "60 tablets"],
        ["Refills:", "5 refills"],
        ["Days Supply:", "30 days"],
    ]

    rx1_table = Table(rx1_data, colWidths=[1.5 * inch, 4.5 * inch])
    rx1_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fff8dc")),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(rx1_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Prescription 2
    elements.append(Paragraph("<b>Rx 2:</b>", styles["Heading3"]))
    rx2_data = [
        ["Medication:", "Atorvastatin (Generic for Lipitor)"],
        ["Strength:", "20 mg"],
        ["Form:", "Tablet"],
        ["Directions:", "Take ONE (1) tablet by mouth ONCE daily at bedtime"],
        ["Quantity:", "30 tablets"],
        ["Refills:", "5 refills"],
        ["Days Supply:", "30 days"],
    ]

    rx2_table = Table(rx2_data, colWidths=[1.5 * inch, 4.5 * inch])
    rx2_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fff8dc")),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(rx2_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Prescription 3 (Continue existing)
    elements.append(Paragraph("<b>Rx 3:</b>", styles["Heading3"]))
    rx3_data = [
        ["Medication:", "Lisinopril"],
        ["Strength:", "10 mg"],
        ["Form:", "Tablet"],
        ["Directions:", "Take ONE (1) tablet by mouth ONCE daily in the morning"],
        ["Quantity:", "30 tablets"],
        ["Refills:", "5 refills"],
        ["Days Supply:", "30 days"],
        ["Note:", "Continue for hypertension management"],
    ]

    rx3_table = Table(rx3_data, colWidths=[1.5 * inch, 4.5 * inch])
    rx3_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fff8dc")),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(rx3_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Important notes
    elements.append(Paragraph("<b>IMPORTANT INSTRUCTIONS:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "• Take Metformin with food to reduce stomach upset<br/>"
            "• Monitor blood glucose levels daily - keep log<br/>"
            "• Report muscle pain or weakness immediately (Atorvastatin side effect)<br/>"
            "• Avoid grapefruit juice (interacts with Atorvastatin)<br/>"
            "• Follow up in 4 weeks for medication adjustment",
            styles["Normal"],
        )
    )

    elements.append(Spacer(1, 0.4 * inch))
    elements.append(
        Paragraph(
            "☐ Substitution Permissible&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;☑ Dispense as Written",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(
        Paragraph(
            "_________________________________<br/>"
            "Dr. Sarah Mitchell, MD<br/>"
            "Digital Signature<br/>"
            "Date: January 23, 2024",
            styles["Normal"],
        )
    )

    doc.build(elements)
    print(f"✓ Created: {filename}")


def generate_followup_visit():
    """Generate 3-month follow-up visit PDF."""
    filename = f"{OUTPUT_DIR}/04_followup_visit_2024_04_15.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    create_header(
        elements,
        styles,
        "City General Hospital",
        "FOLLOW-UP VISIT NOTE",
        "April 15, 2024",
    )

    # Patient Info
    patient_data = [
        ["Patient:", "John Anderson", "DOB:", "05/12/1978 (45 years)"],
        ["MRN:", "MRN-2024-001", "Visit Type:", "3-Month Follow-up"],
    ]

    t = Table(patient_data, colWidths=[1.2 * inch, 2 * inch, 1 * inch, 2 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f4f8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 0.3 * inch))

    # Subjective
    elements.append(Paragraph("<b>SUBJECTIVE:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "Patient reports significant improvement since starting diabetes medications. "
            "Fatigue has resolved, no more excessive thirst or urination. Has been checking blood glucose daily - "
            "fasting readings now 100-115 mg/dL (down from 150s). Following diet recommendations, walking 30 minutes "
            "5 days/week. No side effects from medications. Lost 8 lbs since last visit.",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    # Objective
    elements.append(Paragraph("<b>OBJECTIVE:</b>", styles["Heading3"]))
    vitals_data = [
        ["Blood Pressure:", "128/82 mmHg ✓", "Heart Rate:", "72 bpm"],
        ["Weight:", "184 lbs (83.5 kg)", "BMI:", "26.4"],
        ["Temperature:", "98.4°F", "O2 Sat:", "98%"],
    ]

    vt = Table(vitals_data, colWidths=[1.5 * inch, 1.8 * inch, 1.2 * inch, 1.5 * inch])
    vt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f0f0f0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(vt)
    elements.append(Spacer(1, 0.2 * inch))

    # Recent Labs
    elements.append(Paragraph("<b>Recent Labs (04/14/2024):</b>", styles["Normal"]))
    lab_data = [
        ["HbA1c:", "6.5% (was 7.8%)", "↓ Improved"],
        ["Fasting Glucose:", "105 mg/dL (was 156)", "↓ Improved"],
        ["LDL Cholesterol:", "118 mg/dL (was 165)", "↓ Improved"],
        ["Total Cholesterol:", "195 mg/dL (was 245)", "↓ Improved"],
    ]

    lab_table = Table(lab_data, colWidths=[2 * inch, 2.5 * inch, 1.5 * inch])
    lab_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f8ff")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (2, 0), (2, -1), colors.green),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ]
        )
    )
    elements.append(lab_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Assessment
    elements.append(Paragraph("<b>ASSESSMENT:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "1. <b>Type 2 Diabetes Mellitus (T2DM)</b> - Well controlled on current regimen (HbA1c 6.5%)<br/>"
            "2. <b>Hypertension (HTN)</b> - Well controlled (128/82 mmHg)<br/>"
            "3. <b>Hyperlipidemia</b> - Improved on statin therapy<br/>"
            "4. <b>Weight loss</b> - Good progress with lifestyle modifications",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    # Plan
    elements.append(Paragraph("<b>PLAN:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "1. <b>Continue current medications:</b><br/>"
            "&nbsp;&nbsp;• Metformin 500mg BID<br/>"
            "&nbsp;&nbsp;• Atorvastatin 20mg daily<br/>"
            "&nbsp;&nbsp;• Lisinopril 10mg daily<br/>"
            "2. <b>Continue lifestyle modifications</b> - diet and exercise<br/>"
            "3. <b>Home glucose monitoring</b> - reduce to 3x per week<br/>"
            "4. <b>Repeat HbA1c</b> in 3 months<br/>"
            "5. <b>Follow-up</b> in 3 months or sooner if concerns",
            styles["Normal"],
        )
    )

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(
        Paragraph(
            "Patient Education: Discussed target HbA1c < 7%, importance of medication adherence, "
            "and warning signs of hypoglycemia. Patient demonstrates good understanding.",
            styles["Normal"],
        )
    )

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(
        Paragraph(
            "_________________________________<br/>"
            "Dr. Sarah Mitchell, MD<br/>"
            "Internal Medicine",
            styles["Normal"],
        )
    )

    doc.build(elements)
    print(f"✓ Created: {filename}")


def generate_cardiology_referral():
    """Generate cardiology referral PDF."""
    filename = f"{OUTPUT_DIR}/05_cardiology_referral_2024_05_10.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    create_header(
        elements,
        styles,
        "Heart & Vascular Institute",
        "CARDIOLOGY CONSULTATION",
        "May 10, 2024",
    )

    # Patient Info
    patient_data = [
        ["Patient:", "John Anderson", "DOB:", "05/12/1978 (46 years)"],
        ["MRN:", "MRN-2024-001", "Referring MD:", "Dr. Sarah Mitchell"],
        [
            "Reason:",
            "Cardiovascular risk assessment - new diagnosis diabetes + HTN",
            "",
            "",
        ],
    ]

    t = Table(patient_data, colWidths=[1.2 * inch, 3 * inch, 1 * inch, 2 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ffe8e8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("SPAN", (1, 2), (3, 2)),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 0.3 * inch))

    # History
    elements.append(Paragraph("<b>HISTORY OF PRESENT ILLNESS:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "46-year-old male referred for cardiovascular risk stratification. Recently diagnosed with "
            "Type 2 Diabetes Mellitus (HbA1c 6.5%, previously 7.8%) and long-standing hypertension. "
            "Strong family history of cardiovascular disease (father MI at age 58). Patient has been compliant "
            "with medications and lifestyle modifications.",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    # Physical Exam
    elements.append(Paragraph("<b>PHYSICAL EXAMINATION:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "BP: 130/84 mmHg, HR: 68 bpm regular, BMI: 26.4<br/>"
            "Cardiovascular: Regular rate and rhythm, no murmurs, rubs, or gallops. Normal S1/S2. "
            "Peripheral pulses 2+ bilaterally. No peripheral edema.<br/>"
            "Lungs: Clear to auscultation bilaterally",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    # Tests Ordered
    elements.append(Paragraph("<b>DIAGNOSTIC TESTS ORDERED:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "1. <b>Echocardiogram</b> - assess cardiac structure and function<br/>"
            "2. <b>Stress Test (Exercise Echo)</b> - evaluate for ischemic heart disease<br/>"
            "3. <b>Carotid Ultrasound</b> - screen for carotid artery disease<br/>"
            "4. <b>Ankle-Brachial Index (ABI)</b> - peripheral vascular assessment",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    # Assessment
    elements.append(Paragraph("<b>ASSESSMENT:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "1. <b>Intermediate cardiovascular risk</b> - Multiple risk factors (diabetes, HTN, family history, age)<br/>"
            "2. <b>Type 2 Diabetes Mellitus</b> - Currently well controlled<br/>"
            "3. <b>Essential Hypertension</b> - Adequately controlled on Lisinopril<br/>"
            "4. <b>Hyperlipidemia</b> - On statin therapy, LDL near goal",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    # Recommendations
    elements.append(Paragraph("<b>RECOMMENDATIONS:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "1. <b>Aspirin</b> 81mg daily for cardiovascular prevention<br/>"
            "2. <b>Continue current medications</b> (Metformin, Atorvastatin, Lisinopril)<br/>"
            "3. <b>Target LDL < 70 mg/dL</b> given diabetes - may need statin dose increase<br/>"
            "4. <b>Annual cardiovascular screening</b> recommended<br/>"
            "5. <b>Follow up</b> after test results (scheduled 05/25/2024)",
            styles["Normal"],
        )
    )

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(
        Paragraph(
            "_________________________________<br/>"
            "Dr. Michael Rodriguez, MD, FACC<br/>"
            "Board Certified Cardiologist<br/>"
            "Heart & Vascular Institute",
            styles["Normal"],
        )
    )

    doc.build(elements)
    print(f"✓ Created: {filename}")


def generate_echo_results():
    """Generate echocardiogram results PDF."""
    filename = f"{OUTPUT_DIR}/06_echo_results_2024_05_18.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    create_header(
        elements,
        styles,
        "Heart & Vascular Institute - Imaging",
        "ECHOCARDIOGRAM REPORT",
        "May 18, 2024",
    )

    # Patient Info
    patient_data = [
        ["Patient:", "John Anderson", "DOB:", "05/12/1978"],
        ["MRN:", "MRN-2024-001", "Ordering MD:", "Dr. Michael Rodriguez"],
        [
            "Exam Date:",
            "05/18/2024 10:30 AM",
            "Study:",
            "Transthoracic Echo with Doppler",
        ],
    ]

    t = Table(patient_data, colWidths=[1.5 * inch, 2.5 * inch, 1.2 * inch, 2 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f8ff")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 0.3 * inch))

    # Indication
    elements.append(Paragraph("<b>INDICATION:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "Cardiovascular risk assessment. Newly diagnosed Type 2 Diabetes and hypertension. "
            "Baseline cardiac function evaluation.",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    # Technical Quality
    elements.append(
        Paragraph(
            "<b>TECHNICAL QUALITY:</b> Adequate for interpretation", styles["Normal"]
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    # Findings
    elements.append(Paragraph("<b>FINDINGS:</b>", styles["Heading3"]))

    findings_data = [
        ["Parameter", "Measurement", "Normal Range", "Interpretation"],
        ["Left Ventricular Size", "Normal", "", "✓ Normal"],
        ["LV Ejection Fraction (EF)", "60%", "55-70%", "✓ Normal"],
        ["LV Wall Motion", "Normal", "", "✓ Normal"],
        ["LV Mass Index", "95 g/m²", "< 115 g/m²", "✓ Normal"],
        ["Left Atrium Size", "Mildly dilated", "", "⚠ Mild"],
        ["Right Ventricle", "Normal size/function", "", "✓ Normal"],
        ["Aortic Valve", "Trileaflet, normal", "", "✓ Normal"],
        ["Mitral Valve", "Normal", "", "✓ Normal"],
        ["Tricuspid Valve", "Normal", "", "✓ Normal"],
        ["Pericardium", "No effusion", "", "✓ Normal"],
    ]

    findings_table = Table(
        findings_data, colWidths=[2 * inch, 1.5 * inch, 1.2 * inch, 1.5 * inch]
    )
    findings_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4a90e2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("TEXTCOLOR", (3, 5), (3, 5), colors.orange),
            ]
        )
    )
    elements.append(findings_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Impression
    elements.append(Paragraph("<b>IMPRESSION:</b>", styles["Heading3"]))
    elements.append(
        Paragraph(
            "1. <b>Normal left ventricular size and systolic function</b> (EF 60%)<br/>"
            "2. <b>Mild left atrial enlargement</b> - may be related to hypertension<br/>"
            "3. <b>No significant valvular abnormalities</b><br/>"
            "4. <b>No pericardial effusion</b><br/><br/>"
            "<b>Overall:</b> Reassuring cardiac structure and function. Mild LA enlargement suggests "
            "good blood pressure control is important. Recommend continued medical management.",
            styles["Normal"],
        )
    )

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(
        Paragraph(
            "_________________________________<br/>"
            "Dr. Emily Zhang, MD<br/>"
            "Board Certified Cardiologist<br/>"
            "Fellowship-trained in Echocardiography<br/>"
            "Electronically signed: 05/18/2024 15:45",
            styles["Normal"],
        )
    )

    doc.build(elements)
    print(f"✓ Created: {filename}")


def main():
    """Generate all test PDFs."""
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n" + "=" * 60)
    print("🏥 GENERATING REALISTIC MEDICAL TEST DOCUMENTS")
    print("=" * 60)
    print(f"\nOutput directory: {OUTPUT_DIR}\n")

    # Generate all documents
    print("Creating comprehensive patient medical history...\n")

    generate_initial_consultation()
    generate_lab_results()
    generate_diabetes_prescription()
    generate_followup_visit()
    generate_cardiology_referral()
    generate_echo_results()

    print("\n" + "=" * 60)
    print("✅ ALL TEST DOCUMENTS GENERATED SUCCESSFULLY")
    print("=" * 60)
    print(f"\n📁 6 realistic medical PDFs created in: {OUTPUT_DIR}")
    print("\nDocument Timeline:")
    print("  1. Initial Consultation (Jan 15, 2024) - Diabetes suspected")
    print("  2. Lab Results (Jan 22, 2024) - Diabetes confirmed")
    print("  3. Prescription (Jan 23, 2024) - Started Metformin + Statin")
    print("  4. Follow-up Visit (Apr 15, 2024) - Great improvement!")
    print("  5. Cardiology Referral (May 10, 2024) - CV risk assessment")
    print("  6. Echocardiogram (May 18, 2024) - Normal heart function")
    print("\nThese documents will test:")
    print("  ✓ Agent 1 (Validator) - Document quality")
    print("  ✓ Agent 5 (Context) - Patient history retrieval")
    print("  ✓ Agent 2 (Extractor) - Clinical data extraction")
    print("  ✓ Agent 3 (Summarizer) - Dual summaries + timeline events")
    print("  ✓ Agent 6 (Relationship Mapper) - Entity relationships")
    print("  ✓ Smart Embeddings - Search-optimized summaries")
    print("\n🚀 Ready to upload and test the 5-agent system!\n")


if __name__ == "__main__":
    main()
