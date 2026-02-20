"""
Generate realistic synthetic medical documents for testing Medrix.
Creates PDFs and images that look like real medical documents.

Usage:
    python scripts/generate_test_documents.py
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime, timedelta
import random
import os


class MedicalDocumentGenerator:
    """Generate synthetic medical documents for testing."""

    def __init__(self, output_dir="test_data"):
        """Initialize generator with output directory."""
        self.output_dir = output_dir
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self._ensure_output_dirs()

    def _setup_custom_styles(self):
        """Create custom paragraph styles."""
        self.styles.add(
            ParagraphStyle(
                name="Header",
                parent=self.styles["Heading1"],
                fontSize=16,
                textColor=colors.HexColor("#1a56db"),
                spaceAfter=6,
                alignment=TA_CENTER,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SubHeader",
                parent=self.styles["Heading2"],
                fontSize=12,
                textColor=colors.HexColor("#1f2937"),
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="Small",
                parent=self.styles["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#6b7280"),
            )
        )

    def _ensure_output_dirs(self):
        """Create output directory structure."""
        dirs = [
            self.output_dir,
            f"{self.output_dir}/lab_reports",
            f"{self.output_dir}/prescriptions",
            f"{self.output_dir}/imaging",
            f"{self.output_dir}/discharge_summaries",
            f"{self.output_dir}/consultation_notes",
            f"{self.output_dir}/invalid",
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)

    def generate_lab_report(self, filename, patient_name="John Doe", abnormal=True):
        """Generate a lab report with blood test results."""
        filepath = f"{self.output_dir}/lab_reports/{filename}"
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []

        # Header
        story.append(Paragraph("City Medical Center", self.styles["Header"]))
        story.append(
            Paragraph("Laboratory Services Department", self.styles["SubHeader"])
        )
        story.append(
            Paragraph(
                "123 Healthcare Ave, Medical City, MC 12345 | Tel: (555) 123-4567",
                self.styles["Small"],
            )
        )
        story.append(Spacer(1, 0.3 * inch))

        # Patient Info
        test_date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime(
            "%Y-%m-%d"
        )
        patient_info = [
            ["Patient Name:", patient_name, "Date of Birth:", "1985-06-15"],
            [
                "Patient ID:",
                f"MRN{random.randint(100000, 999999)}",
                "Test Date:",
                test_date,
            ],
            [
                "Ordering Physician:",
                "Dr. Sarah Johnson, MD",
                "Report Date:",
                datetime.now().strftime("%Y-%m-%d"),
            ],
        ]

        t = Table(patient_info, colWidths=[1.5 * inch, 2 * inch, 1.5 * inch, 2 * inch])
        t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 0.3 * inch))

        # Lab Results
        story.append(Paragraph("Complete Blood Count (CBC)", self.styles["SubHeader"]))

        # Generate realistic lab values
        if abnormal:
            glucose = random.randint(150, 200)  # High
            glucose_flag = "HIGH"
            glucose_color = colors.red
            hba1c = round(random.uniform(6.5, 8.5), 1)  # High
            hba1c_flag = "HIGH"
            hba1c_color = colors.red
        else:
            glucose = random.randint(70, 100)
            glucose_flag = ""
            glucose_color = colors.black
            hba1c = round(random.uniform(4.5, 5.6), 1)
            hba1c_flag = ""
            hba1c_color = colors.black

        lab_data = [
            ["Test Name", "Value", "Unit", "Reference Range", "Flag"],
            [
                "Hemoglobin",
                str(round(random.uniform(13.5, 17.5), 1)),
                "g/dL",
                "13.5-17.5",
                "",
            ],
            [
                "WBC",
                str(round(random.uniform(4.5, 11.0), 1)),
                "K/uL",
                "4.5-11.0",
                "",
            ],
            ["Platelets", str(random.randint(150, 400)), "K/uL", "150-400", ""],
            ["Glucose", str(glucose), "mg/dL", "70-100", glucose_flag],
            ["HbA1c", str(hba1c), "%", "<5.7", hba1c_flag],
            [
                "Creatinine",
                str(round(random.uniform(0.7, 1.3), 1)),
                "mg/dL",
                "0.7-1.3",
                "",
            ],
            ["ALT", str(random.randint(7, 56)), "U/L", "7-56", ""],
            ["AST", str(random.randint(10, 40)), "U/L", "10-40", ""],
            [
                "Total Cholesterol",
                str(random.randint(125, 200)),
                "mg/dL",
                "<200",
                "",
            ],
            ["HDL", str(random.randint(40, 60)), "mg/dL", ">40", ""],
            ["LDL", str(random.randint(70, 130)), "mg/dL", "<100", ""],
        ]

        t = Table(
            lab_data, colWidths=[2.5 * inch, 1 * inch, 1 * inch, 1.5 * inch, 1 * inch]
        )
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a56db")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f9fafb")],
                    ),
                ]
            )
        )

        # Color abnormal values
        if abnormal:
            t.setStyle(
                TableStyle(
                    [
                        ("TEXTCOLOR", (1, 4), (1, 4), glucose_color),  # Glucose
                        ("TEXTCOLOR", (4, 4), (4, 4), glucose_color),  # Glucose flag
                        ("TEXTCOLOR", (1, 5), (1, 5), hba1c_color),  # HbA1c
                        ("TEXTCOLOR", (4, 5), (4, 5), hba1c_color),  # HbA1c flag
                        ("FONTNAME", (4, 4), (4, 5), "Helvetica-Bold"),
                    ]
                )
            )

        story.append(t)
        story.append(Spacer(1, 0.2 * inch))

        # Clinical Notes
        story.append(Paragraph("Clinical Notes:", self.styles["SubHeader"]))
        if abnormal:
            notes = "Elevated glucose and HbA1c levels indicate poor glycemic control. Recommend endocrinology consultation and adjustment of diabetes management plan. Follow-up testing recommended in 3 months."
        else:
            notes = "All values within normal limits. Continue current health maintenance plan. Routine follow-up in 12 months."

        story.append(Paragraph(notes, self.styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # Footer
        story.append(
            Paragraph(
                "Electronically signed by: Dr. Michael Chen, MD - Laboratory Director",
                self.styles["Small"],
            )
        )
        story.append(
            Paragraph(
                f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                self.styles["Small"],
            )
        )

        doc.build(story)
        print(f"✓ Generated: {filepath}")

    def generate_prescription(
        self, filename, patient_name="Jane Smith", num_medications=3
    ):
        """Generate a prescription document."""
        filepath = f"{self.output_dir}/prescriptions/{filename}"
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []

        # Header
        story.append(Paragraph("Medical Clinic", self.styles["Header"]))
        story.append(
            Paragraph("Dr. Sarah Johnson, MD - Cardiology", self.styles["SubHeader"])
        )
        story.append(
            Paragraph(
                "456 Medical Plaza, Health City, HC 54321 | Tel: (555) 987-6543",
                self.styles["Small"],
            )
        )
        story.append(Spacer(1, 0.3 * inch))

        # Patient & Date
        rx_date = datetime.now().strftime("%Y-%m-%d")
        patient_info = [
            ["Patient:", patient_name, "Date:", rx_date],
            ["DOB:", "1975-03-20", "MRN:", f"PAT{random.randint(100000, 999999)}"],
        ]

        t = Table(patient_info, colWidths=[1 * inch, 3 * inch, 1 * inch, 2 * inch])
        t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 0.3 * inch))

        # Allergies
        story.append(
            Paragraph(
                "<b>Known Allergies:</b> Penicillin (severe rash), Sulfa drugs (hives)",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # Prescriptions
        story.append(Paragraph("Rx", self.styles["SubHeader"]))

        medications = [
            {
                "name": "Metformin",
                "generic": "Metformin hydrochloride",
                "dose": "500mg",
                "route": "Oral",
                "freq": "Twice daily (BID)",
                "instructions": "Take with meals to reduce GI upset",
            },
            {
                "name": "Lisinopril",
                "generic": "Lisinopril",
                "dose": "10mg",
                "route": "Oral",
                "freq": "Once daily",
                "instructions": "Take in the morning",
            },
            {
                "name": "Atorvastatin",
                "generic": "Atorvastatin calcium",
                "dose": "20mg",
                "route": "Oral",
                "freq": "Once daily",
                "instructions": "Take at bedtime",
            },
            {
                "name": "Aspirin",
                "generic": "Acetylsalicylic acid",
                "dose": "81mg",
                "route": "Oral",
                "freq": "Once daily",
                "instructions": "Take with food",
            },
            {
                "name": "Omeprazole",
                "generic": "Omeprazole",
                "dose": "20mg",
                "route": "Oral",
                "freq": "Once daily",
                "instructions": "Take 30 minutes before breakfast",
            },
        ]

        selected_meds = medications[:num_medications]

        for i, med in enumerate(selected_meds, 1):
            story.append(
                Paragraph(
                    f"<b>{i}. {med['name']} ({med['generic']})</b>",
                    self.styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;Dosage: {med['dose']}",
                    self.styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;Route: {med['route']}",
                    self.styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;Frequency: {med['freq']}",
                    self.styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;Instructions: {med['instructions']}",
                    self.styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;Quantity: 90 tablets | Refills: 3",
                    self.styles["Normal"],
                )
            )
            story.append(Spacer(1, 0.15 * inch))

        # Clinical Notes
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("Clinical Notes:", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                "Patient diagnosed with Type 2 Diabetes, Hypertension, and Hyperlipidemia. "
                "Medications adjusted to optimize glycemic control and cardiovascular risk reduction. "
                "Patient counseled on lifestyle modifications including diet and exercise.",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        story.append(
            Paragraph(
                "<b>Follow-up:</b> Return in 3 months for lab work (fasting glucose, HbA1c, lipid panel) "
                "and blood pressure check.",
                self.styles["Normal"],
            )
        )

        story.append(Spacer(1, 0.4 * inch))

        # Signature
        story.append(Paragraph("_" * 40, self.styles["Normal"]))
        story.append(
            Paragraph("Dr. Sarah Johnson, MD - Cardiology", self.styles["Normal"])
        )
        story.append(
            Paragraph(f"DEA#: DJ1234563 | Date: {rx_date}", self.styles["Small"])
        )

        doc.build(story)
        print(f"✓ Generated: {filepath}")

    def generate_xray_report(self, filename, patient_name="Robert Williams"):
        """Generate a chest X-ray report."""
        filepath = f"{self.output_dir}/imaging/{filename}"
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []

        # Header
        story.append(Paragraph("Regional Medical Center", self.styles["Header"]))
        story.append(Paragraph("Radiology Department", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                "789 Hospital Drive, Medical City, MC 67890 | Tel: (555) 246-8135",
                self.styles["Small"],
            )
        )
        story.append(Spacer(1, 0.3 * inch))

        # Exam Info
        exam_date = (datetime.now() - timedelta(days=random.randint(1, 7))).strftime(
            "%Y-%m-%d"
        )
        exam_info = [
            ["Examination:", "CHEST X-RAY, PA AND LATERAL", "", ""],
            ["Patient:", patient_name, "DOB:", "1960-11-25"],
            ["MRN:", f"MRN{random.randint(100000, 999999)}", "Exam Date:", exam_date],
            [
                "Ordering Physician:",
                "Dr. Emily Chen, MD",
                "Report Date:",
                datetime.now().strftime("%Y-%m-%d"),
            ],
        ]

        t = Table(exam_info, colWidths=[1.5 * inch, 2.5 * inch, 1 * inch, 2 * inch])
        t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 0.3 * inch))

        # Clinical History
        story.append(Paragraph("CLINICAL HISTORY:", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                "Chronic cough and shortness of breath. Rule out pneumonia.",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # Comparison
        story.append(Paragraph("COMPARISON:", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                f"Chest X-ray dated {(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')}",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # Technique
        story.append(Paragraph("TECHNIQUE:", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                "PA and lateral views of the chest were obtained.",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # Findings
        story.append(Paragraph("FINDINGS:", self.styles["SubHeader"]))
        findings = [
            "The heart size is within normal limits.",
            "The mediastinal and hilar contours are unremarkable.",
            "The lungs are clear without focal consolidation, effusion, or pneumothorax.",
            "No acute bony abnormalities are identified.",
            "The visualized upper abdomen is unremarkable.",
        ]
        for finding in findings:
            story.append(Paragraph(f"• {finding}", self.styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Impression
        story.append(Paragraph("IMPRESSION:", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                "<b>No acute cardiopulmonary disease.</b>",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.4 * inch))

        # Radiologist signature
        story.append(Paragraph("_" * 50, self.styles["Normal"]))
        story.append(
            Paragraph(
                "Electronically signed by: Dr. James Martinez, MD - Board Certified Radiologist",
                self.styles["Small"],
            )
        )
        story.append(
            Paragraph(
                f"Report finalized: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                self.styles["Small"],
            )
        )

        doc.build(story)
        print(f"✓ Generated: {filepath}")

    def generate_discharge_summary(self, filename, patient_name="Maria Garcia"):
        """Generate a hospital discharge summary."""
        filepath = f"{self.output_dir}/discharge_summaries/{filename}"
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []

        # Header
        story.append(Paragraph("Community Hospital", self.styles["Header"]))
        story.append(Paragraph("Discharge Summary", self.styles["SubHeader"]))
        story.append(Spacer(1, 0.2 * inch))

        # Patient Info
        admit_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        discharge_date = datetime.now().strftime("%Y-%m-%d")

        patient_info = [
            ["Patient:", patient_name, "DOB:", "1968-09-12"],
            ["MRN:", f"MRN{random.randint(100000, 999999)}", "Age:", "57 years"],
            ["Admission Date:", admit_date, "Discharge Date:", discharge_date],
            ["Attending Physician:", "Dr. Robert Thompson, MD", "", ""],
        ]

        t = Table(
            patient_info, colWidths=[1.5 * inch, 2.5 * inch, 1.5 * inch, 2 * inch]
        )
        t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 0.3 * inch))

        # Admission Diagnosis
        story.append(Paragraph("ADMISSION DIAGNOSIS:", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                "Acute exacerbation of congestive heart failure (CHF)",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # Discharge Diagnosis
        story.append(Paragraph("DISCHARGE DIAGNOSIS:", self.styles["SubHeader"]))
        diagnoses = [
            "1. Acute decompensated heart failure with reduced ejection fraction (HFrEF)",
            "2. Hypertension",
            "3. Type 2 Diabetes Mellitus",
            "4. Chronic kidney disease, stage 3",
        ]
        for dx in diagnoses:
            story.append(Paragraph(dx, self.styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Hospital Course
        story.append(Paragraph("HOSPITAL COURSE:", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                "Patient is a 57-year-old female who presented to the emergency department with "
                "progressive dyspnea, orthopnea, and lower extremity edema over the past week. "
                "Physical examination revealed bilateral crackles, elevated JVP, and 2+ pitting edema. "
                "Chest X-ray showed pulmonary congestion. BNP was elevated at 1850 pg/mL. "
                "Echocardiogram revealed EF of 30%. Patient was admitted for IV diuresis and "
                "optimization of heart failure medications.",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.15 * inch))
        story.append(
            Paragraph(
                "Patient responded well to IV Lasix with improvement in dyspnea and net negative "
                "fluid balance of 6 liters over 4 days. Creatinine remained stable. Heart failure "
                "medications were titrated. Patient was transitioned to oral diuretics and was "
                "hemodynamically stable for discharge.",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # Procedures
        story.append(Paragraph("PROCEDURES PERFORMED:", self.styles["SubHeader"]))
        story.append(Paragraph("• Transthoracic echocardiogram", self.styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Discharge Medications
        story.append(Paragraph("DISCHARGE MEDICATIONS:", self.styles["SubHeader"]))
        meds = [
            "1. Furosemide 40mg PO twice daily",
            "2. Carvedilol 6.25mg PO twice daily",
            "3. Lisinopril 10mg PO daily",
            "4. Spironolactone 25mg PO daily",
            "5. Metformin 1000mg PO twice daily",
            "6. Aspirin 81mg PO daily",
            "7. Atorvastatin 40mg PO at bedtime",
        ]
        for med in meds:
            story.append(Paragraph(med, self.styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Discharge Instructions
        story.append(Paragraph("DISCHARGE INSTRUCTIONS:", self.styles["SubHeader"]))
        instructions = [
            "• Daily weights - call if gain > 3 lbs in 2 days",
            "• Sodium restriction to 2 grams per day",
            "• Fluid restriction to 1.5 liters per day",
            "• Monitor blood pressure daily",
            "• Follow up with cardiology in 1 week",
            "• Follow up with primary care in 2 weeks",
            "• Obtain lab work (BMP, CBC) in 1 week",
        ]
        for instr in instructions:
            story.append(Paragraph(instr, self.styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # Signature
        story.append(Paragraph("_" * 50, self.styles["Normal"]))
        story.append(
            Paragraph(
                "Electronically signed by: Dr. Robert Thompson, MD - Internal Medicine",
                self.styles["Small"],
            )
        )
        story.append(
            Paragraph(
                f"Discharge summary completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                self.styles["Small"],
            )
        )

        doc.build(story)
        print(f"✓ Generated: {filepath}")

    def generate_consultation_note(self, filename, patient_name="David Lee"):
        """Generate a consultation note."""
        filepath = f"{self.output_dir}/consultation_notes/{filename}"
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []

        # Header
        story.append(Paragraph("Specialty Medical Group", self.styles["Header"]))
        story.append(Paragraph("Endocrinology Consultation", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                "Dr. Patricia Williams, MD - Board Certified Endocrinologist",
                self.styles["Small"],
            )
        )
        story.append(Spacer(1, 0.3 * inch))

        # Patient & Visit Info
        visit_date = datetime.now().strftime("%Y-%m-%d")
        patient_info = [
            ["Patient:", patient_name, "Visit Date:", visit_date],
            ["DOB:", "1972-04-08", "Age:", "53 years"],
            ["Referring Physician:", "Dr. Sarah Johnson, MD", "", ""],
        ]

        t = Table(
            patient_info, colWidths=[1.5 * inch, 2.5 * inch, 1.5 * inch, 2 * inch]
        )
        t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 0.3 * inch))

        # Chief Complaint
        story.append(Paragraph("CHIEF COMPLAINT:", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                "Diabetes management and elevated HbA1c",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # Vital Signs
        story.append(Paragraph("VITAL SIGNS:", self.styles["SubHeader"]))
        vitals_data = [
            ["Blood Pressure:", "138/88 mmHg (sitting)", "Heart Rate:", "78 bpm"],
            ["Temperature:", "98.6°F (37.0°C)", "Respiratory Rate:", "16/min"],
            ["Weight:", "205 lbs (93 kg)", "Height:", "5'10\" (178 cm)"],
            ["BMI:", "29.4 kg/m²", "SpO2:", "98% on room air"],
        ]

        t = Table(vitals_data, colWidths=[1.5 * inch, 2.5 * inch, 1.5 * inch, 2 * inch])
        t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))

        # History of Present Illness
        story.append(Paragraph("HISTORY OF PRESENT ILLNESS:", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                "53-year-old male with Type 2 Diabetes Mellitus diagnosed 8 years ago. "
                "Currently on Metformin 1000mg BID. Recent HbA1c 8.2% (up from 7.1% six months ago). "
                "Patient reports increased stress at work and admits to dietary non-compliance. "
                "Experiencing increased urination and occasional blurred vision. No hypoglycemic episodes. "
                "Home glucose monitoring shows fasting values 140-180 mg/dL.",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # Past Medical History
        story.append(Paragraph("PAST MEDICAL HISTORY:", self.styles["SubHeader"]))
        pmh = [
            "• Type 2 Diabetes Mellitus (2018)",
            "• Hypertension (2016)",
            "• Hyperlipidemia (2015)",
            "• Overweight/Obesity",
        ]
        for item in pmh:
            story.append(Paragraph(item, self.styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Current Medications
        story.append(Paragraph("CURRENT MEDICATIONS:", self.styles["SubHeader"]))
        meds = [
            "1. Metformin 1000mg PO BID",
            "2. Lisinopril 10mg PO daily",
            "3. Atorvastatin 20mg PO at bedtime",
        ]
        for med in meds:
            story.append(Paragraph(med, self.styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Assessment & Plan
        story.append(Paragraph("ASSESSMENT & PLAN:", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                "<b>1. Type 2 Diabetes Mellitus, uncontrolled (HbA1c 8.2%)</b>",
                self.styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                "&nbsp;&nbsp;&nbsp;&nbsp;• Add Empagliflozin 10mg PO daily (SGLT2 inhibitor)",
                self.styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                "&nbsp;&nbsp;&nbsp;&nbsp;• Continue Metformin 1000mg PO BID",
                self.styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                "&nbsp;&nbsp;&nbsp;&nbsp;• Diabetes education referral for diet counseling",
                self.styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                "&nbsp;&nbsp;&nbsp;&nbsp;• Target HbA1c < 7%",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        story.append(
            Paragraph(
                "<b>2. Hypertension, on treatment</b>",
                self.styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                "&nbsp;&nbsp;&nbsp;&nbsp;• Increase Lisinopril to 20mg PO daily",
                self.styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                "&nbsp;&nbsp;&nbsp;&nbsp;• Home BP monitoring",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        story.append(
            Paragraph(
                "<b>3. Overweight (BMI 29.4)</b>",
                self.styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                "&nbsp;&nbsp;&nbsp;&nbsp;• Dietary counseling and exercise program",
                self.styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                "&nbsp;&nbsp;&nbsp;&nbsp;• Target weight loss 5-10%",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # Follow-up
        story.append(Paragraph("FOLLOW-UP:", self.styles["SubHeader"]))
        story.append(
            Paragraph(
                "• Return visit in 3 months with repeat HbA1c, BMP, lipid panel",
                self.styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                "• Annual eye exam and foot exam scheduled",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.3 * inch))

        # Signature
        story.append(Paragraph("_" * 50, self.styles["Normal"]))
        story.append(
            Paragraph(
                "Dr. Patricia Williams, MD - Endocrinology",
                self.styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                f"Note completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                self.styles["Small"],
            )
        )

        doc.build(story)
        print(f"✓ Generated: {filepath}")

    def generate_all_test_documents(self):
        """Generate complete test dataset."""
        print("\n" + "=" * 60)
        print("🏥 GENERATING MEDICAL TEST DOCUMENTS")
        print("=" * 60 + "\n")

        # Lab Reports
        print("📋 Generating Lab Reports...")
        self.generate_lab_report("lab_report_normal.pdf", "John Doe", abnormal=False)
        self.generate_lab_report(
            "lab_report_high_glucose.pdf", "Jane Smith", abnormal=True
        )
        self.generate_lab_report(
            "lab_report_diabetes.pdf", "Robert Williams", abnormal=True
        )

        # Prescriptions
        print("\n💊 Generating Prescriptions...")
        self.generate_prescription(
            "prescription_single_med.pdf", "Sarah Johnson", num_medications=1
        )
        self.generate_prescription(
            "prescription_multiple_meds.pdf", "Michael Brown", num_medications=3
        )
        self.generate_prescription(
            "prescription_complex.pdf", "Emily Davis", num_medications=5
        )

        # Imaging
        print("\n🔬 Generating Imaging Reports...")
        self.generate_xray_report("chest_xray_normal.pdf", "David Wilson")
        self.generate_xray_report("chest_xray_report.pdf", "Lisa Anderson")

        # Discharge Summaries
        print("\n🏥 Generating Discharge Summaries...")
        self.generate_discharge_summary("hospital_discharge.pdf", "Maria Garcia")
        self.generate_discharge_summary("cardiac_discharge.pdf", "Thomas Martinez")

        # Consultation Notes
        print("\n👨‍⚕️ Generating Consultation Notes...")
        self.generate_consultation_note("endocrinology_consult.pdf", "David Lee")
        self.generate_consultation_note("cardiology_consult.pdf", "Jennifer Taylor")

        # Create a simple blank PDF for invalid test
        print("\n❌ Creating Invalid Test Files...")
        invalid_path = f"{self.output_dir}/invalid/blank_page.pdf"
        doc = SimpleDocTemplate(invalid_path, pagesize=letter)
        doc.build([Paragraph("", self.styles["Normal"])])
        print(f"✓ Generated: {invalid_path}")

        print("\n" + "=" * 60)
        print("✅ TEST DOCUMENT GENERATION COMPLETE")
        print("=" * 60)
        print(f"\nDocuments saved to: {self.output_dir}/")
        print("\nDirectory structure:")
        print(f"  {self.output_dir}/")
        print("  ├── lab_reports/ (3 files)")
        print("  ├── prescriptions/ (3 files)")
        print("  ├── imaging/ (2 files)")
        print("  ├── discharge_summaries/ (2 files)")
        print("  ├── consultation_notes/ (2 files)")
        print("  └── invalid/ (1 file)")
        print(f"\nTotal: 13 test documents ready for upload!")


if __name__ == "__main__":
    generator = MedicalDocumentGenerator(output_dir="test_data")
    generator.generate_all_test_documents()
