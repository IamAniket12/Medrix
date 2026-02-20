"""Agent persistence service - saves agent outputs to database."""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from ..models import (
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
    SearchTerm,
    AuditLog,
)
from ..utils.normalization import normalize_height, normalize_weight, normalize_date


class AgentPersistenceService:
    """Service to persist agent processing results to database."""

    def __init__(self, db: Session):
        self.db = db

    def save_agent_results(
        self,
        document_id: str,
        user_id: str,
        agent_results: Dict[str, Any],
    ) -> DocumentProcessingResult:
        """
        Save complete agent processing results to database.

        Args:
            document_id: Document ID
            user_id: User ID
            agent_results: Complete agent output dict with validation, clinical_data, summaries

        Returns:
            DocumentProcessingResult object
        """
        try:
            # Extract agent outputs
            validation = agent_results.get("validation", {})
            clinical_data = agent_results.get("clinical_data", {})
            summaries = agent_results.get("summaries", {})

            # Save raw processing result (JSONB storage)
            processing_result = self._save_processing_result(
                document_id, validation, clinical_data, summaries
            )

            # Save denormalized summary
            self._save_document_summary(document_id, summaries)

            # Save normalized clinical data
            self._save_clinical_conditions(
                document_id, user_id, clinical_data.get("conditions", [])
            )
            self._save_clinical_medications(
                document_id, user_id, clinical_data.get("medications", [])
            )
            self._save_clinical_allergies(
                document_id, user_id, clinical_data.get("allergies", [])
            )
            self._save_lab_results(
                document_id, user_id, clinical_data.get("lab_results", [])
            )
            self._save_vital_signs(
                document_id, user_id, clinical_data.get("vital_signs", [])
            )
            self._save_procedures(
                document_id, user_id, clinical_data.get("procedures", [])
            )
            self._save_immunizations(
                document_id, user_id, clinical_data.get("immunizations", [])
            )

            # Save timeline events and search terms
            self._save_timeline_events(
                document_id,
                user_id,
                summaries.get("agent_context", {}),
                clinical_data,
                validation,
            )
            self._save_search_terms(document_id, summaries.get("agent_context", {}))

            # Log audit trail
            self._log_audit(
                user_id, document_id, "process", "Document processed by AI agents"
            )

            self.db.commit()
            return processing_result

        except Exception as e:
            self.db.rollback()
            print(f"⚠️  Database save failed: {str(e)}")

            # Production approach: Try to save partial results
            # Save what we can even if some parts fail
            try:
                # At minimum, save the processing result and summary
                processing_result = self._save_processing_result(
                    document_id, validation, clinical_data, summaries
                )
                self._save_document_summary(document_id, summaries)
                self.db.commit()
                print(f"  ✓ Saved partial results (processing record and summary)")
                return processing_result
            except Exception as e2:
                self.db.rollback()
                print(f"  ❌ Failed to save even partial results: {str(e2)}")
                raise e  # Raise original error

    def _save_processing_result(
        self,
        document_id: str,
        validation: Dict,
        clinical_data: Dict,
        summaries: Dict,
    ) -> DocumentProcessingResult:
        """Save raw agent processing result."""
        result = DocumentProcessingResult(
            id=str(uuid.uuid4()),
            document_id=document_id,
            processing_started_at=datetime.utcnow(),
            processing_completed_at=datetime.utcnow(),
            processing_status="completed",
            validation_result=validation.get("validation"),
            is_valid=validation.get("validation", {}).get("is_valid", False),
            quality_score=validation.get("validation", {}).get("quality_score", 0.0),
            validation_issues=validation.get("validation", {}).get("issues", []),
            document_metadata=validation.get("document_metadata"),
            clinical_data=clinical_data,
            summaries=summaries,
            brief_summary=summaries.get("brief_summary"),
            urgency_level=summaries.get("urgency_level"),
            agent_context=summaries.get("agent_context"),
        )
        self.db.add(result)
        return result

    def _save_document_summary(self, document_id: str, summaries: Dict):
        """Save denormalized document summary."""
        detailed_summary = summaries.get("detailed_summary", {})
        agent_context = summaries.get("agent_context", {})

        summary = DocumentSummary(
            id=str(uuid.uuid4()),
            document_id=document_id,
            brief_summary=summaries.get("brief_summary"),
            search_optimized_summary=summaries.get("search_optimized_summary"),
            clinical_overview=detailed_summary.get("clinical_overview"),
            clinical_significance=detailed_summary.get("clinical_significance"),
            urgency_level=summaries.get("urgency_level"),
            key_findings=detailed_summary.get("key_findings", []),
            treatment_plan=detailed_summary.get("treatment_plan"),
            action_items=detailed_summary.get("action_items", []),
            semantic_keywords=agent_context.get("semantic_keywords", []),
            clinical_relationships=agent_context.get("clinical_relationships", []),
            temporal_events=agent_context.get("temporal_events", []),
            risk_factors=agent_context.get("risk_factors", []),
            missing_information=agent_context.get("missing_information", []),
        )
        self.db.add(summary)

    def _save_clinical_conditions(
        self, document_id: str, user_id: str, conditions: list
    ):
        """Save normalized clinical conditions."""
        for cond in conditions:
            # Validate required fields before saving
            condition_name = cond.get("name")
            if not condition_name or (
                isinstance(condition_name, str) and condition_name.strip() == ""
            ):
                print(f"  ⊘ Skipping condition with missing name")
                continue

            condition = ClinicalCondition(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=user_id,
                name=condition_name,
                status=cond.get("status"),
                diagnosed_date=self._parse_date(cond.get("diagnosed_date")),
                severity=cond.get("severity"),
                body_site=cond.get("body_site"),
                notes=cond.get("notes"),
            )
            self.db.add(condition)

    def _save_clinical_medications(
        self, document_id: str, user_id: str, medications: list
    ):
        """Save normalized medications."""
        for med in medications:
            # Validate required medication name
            med_name = med.get("name")
            if not med_name or (isinstance(med_name, str) and med_name.strip() == ""):
                print(f"  ⊘ Skipping medication with missing name")
                continue

            medication = ClinicalMedication(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=user_id,
                name=med_name,
                dosage=med.get("dosage"),
                frequency=med.get("frequency"),
                route=med.get("route"),
                start_date=self._parse_date(med.get("start_date")),
                end_date=self._parse_date(med.get("end_date")),
                prescriber=med.get("prescriber"),
                indication=med.get("indication"),
                notes=med.get("notes"),
                is_active=True,
            )
            self.db.add(medication)

    def _save_clinical_allergies(self, document_id: str, user_id: str, allergies: list):
        """Save normalized allergies - skip null/empty entries."""
        for allergy_data in allergies:
            allergen = allergy_data.get("allergen")

            # Skip entries with null/empty allergen
            if not allergen or (isinstance(allergen, str) and allergen.strip() == ""):
                print(f"  ⊘ Skipping allergy with null/empty allergen")
                continue

            allergy = ClinicalAllergy(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=user_id,
                allergen=allergen,
                reaction=allergy_data.get("reaction"),
                severity=allergy_data.get("severity"),
                allergy_type=allergy_data.get("allergy_type"),
                verified_date=self._parse_date(allergy_data.get("verified_date")),
                verified_by=allergy_data.get("verified_by"),
                notes=allergy_data.get("notes"),
                is_active=True,
            )
            self.db.add(allergy)

    def _save_lab_results(self, document_id: str, user_id: str, lab_results: list):
        """Save normalized lab results."""
        for lab in lab_results:
            # Validate required test name
            test_name = lab.get("test_name")
            if not test_name or (
                isinstance(test_name, str) and test_name.strip() == ""
            ):
                print(f"  ⊘ Skipping lab result with missing test name")
                continue

            lab_result = ClinicalLabResult(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=user_id,
                test_name=test_name,
                value=str(lab.get("value")) if lab.get("value") is not None else None,
                unit=lab.get("unit"),
                reference_range=lab.get("reference_range"),
                is_abnormal=lab.get("is_abnormal", False),
                abnormal_flag=lab.get("abnormal_flag"),
                test_date=self._parse_date(lab.get("test_date")),
                ordering_provider=lab.get("ordering_provider"),
                lab_facility=lab.get("lab_facility"),
                notes=lab.get("notes"),
            )
            self.db.add(lab_result)

    def _save_vital_signs(self, document_id: str, user_id: str, vital_signs: list):
        """
        Save normalized vital signs.

        Transform from extractor format (typed vitals) to database format (flattened row).
        Extractor returns: [{"type": "blood_pressure", "systolic": 120, "diastolic": 80, ...}, ...]
        Database expects: One row with all vital measurements
        """
        if not vital_signs:
            return

        # Configuration-driven mapping: type -> (source_fields, target_field)
        VITAL_TYPE_MAPPING = {
            "blood_pressure": [
                ("systolic", "systolic_bp"),
                ("diastolic", "diastolic_bp"),
            ],
            "heart_rate": [("value", "heart_rate")],
            "respiratory_rate": [("value", "respiratory_rate")],
            "temperature": [
                ("value", "temperature"),
                ("unit", "temperature_unit"),
            ],
            "oxygen_saturation": [("value", "oxygen_saturation")],
            "spo2": [("value", "oxygen_saturation")],
            "weight": [
                ("value", "weight"),
                ("unit", "weight_unit"),
            ],
            "height": [
                ("value", "height"),
                ("unit", "height_unit"),
            ],
            "bmi": [("value", "bmi")],
        }

        # Group vitals by measurement date
        vitals_by_date = {}

        for vital in vital_signs:
            if not vital or not isinstance(vital, dict):
                continue

            vital_type = vital.get("type", "").lower()
            measured_date = vital.get("measured_date") or vital.get("measurement_date")
            date_key = measured_date if measured_date else "default"

            if date_key not in vitals_by_date:
                vitals_by_date[date_key] = {
                    "measurement_date": measured_date,
                    "systolic_bp": None,
                    "diastolic_bp": None,
                    "heart_rate": None,
                    "respiratory_rate": None,
                    "temperature": None,
                    "temperature_unit": None,
                    "oxygen_saturation": None,
                    "weight": None,
                    "weight_unit": None,
                    "height": None,
                    "height_unit": None,
                    "bmi": None,
                    "notes": None,
                }

            # Apply mapping if type is known
            if vital_type in VITAL_TYPE_MAPPING:
                for source_field, target_field in VITAL_TYPE_MAPPING[vital_type]:
                    value = vital.get(source_field)
                    if value is not None:
                        # Normalize height to cm if needed
                        if target_field == "height":
                            normalized = normalize_height(value)
                            if normalized:
                                vitals_by_date[date_key][target_field] = normalized
                                vitals_by_date[date_key]["height_unit"] = "cm"
                        # Normalize weight
                        elif target_field == "weight":
                            normalized = normalize_weight(
                                value, target_unit=vital.get("unit") or "kg"
                            )
                            if normalized:
                                vitals_by_date[date_key][target_field] = normalized[
                                    "value"
                                ]
                                vitals_by_date[date_key]["weight_unit"] = normalized[
                                    "unit"
                                ]
                        # Store value directly
                        else:
                            vitals_by_date[date_key][target_field] = value

            # Accumulate notes
            if vital.get("notes") or vital.get("measurement_context"):
                note = vital.get("notes") or vital.get("measurement_context")
                if vitals_by_date[date_key]["notes"]:
                    vitals_by_date[date_key]["notes"] += f"; {note}"
                else:
                    vitals_by_date[date_key]["notes"] = note

        # Save each date's vitals as one row
        for date_key, vitals_data in vitals_by_date.items():
            # Skip if ALL measurements are null (empty row)
            has_data = any(
                [
                    vitals_data.get("systolic_bp"),
                    vitals_data.get("diastolic_bp"),
                    vitals_data.get("heart_rate"),
                    vitals_data.get("respiratory_rate"),
                    vitals_data.get("temperature"),
                    vitals_data.get("oxygen_saturation"),
                    vitals_data.get("weight"),
                    vitals_data.get("height"),
                    vitals_data.get("bmi"),
                ]
            )

            if not has_data:
                print(f"  ⊘ Skipping vital signs: No measurements found")
                continue

            vital_sign = ClinicalVitalSign(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=user_id,
                measurement_date=self._parse_datetime(
                    vitals_data.get("measurement_date")
                ),
                systolic_bp=vitals_data.get("systolic_bp"),
                diastolic_bp=vitals_data.get("diastolic_bp"),
                heart_rate=vitals_data.get("heart_rate"),
                respiratory_rate=vitals_data.get("respiratory_rate"),
                temperature=vitals_data.get("temperature"),
                temperature_unit=vitals_data.get("temperature_unit"),
                oxygen_saturation=vitals_data.get("oxygen_saturation"),
                weight=vitals_data.get("weight"),
                weight_unit=vitals_data.get("weight_unit"),
                height=vitals_data.get("height"),
                height_unit=vitals_data.get("height_unit"),
                bmi=vitals_data.get("bmi"),
                notes=vitals_data.get("notes"),
            )
            self.db.add(vital_sign)
            print(f"  ✓ Saved vital signs for date: {date_key}")

    def _save_procedures(self, document_id: str, user_id: str, procedures: list):
        """Save normalized procedures."""
        for proc in procedures:
            procedure = ClinicalProcedure(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=user_id,
                procedure_name=proc.get("procedure_name"),
                performed_date=self._parse_date(proc.get("performed_date")),
                provider=proc.get("provider"),
                facility=proc.get("facility"),
                body_site=proc.get("body_site"),
                indication=proc.get("indication"),
                outcome=proc.get("outcome"),
                notes=proc.get("notes"),
            )
            self.db.add(procedure)

    def _save_immunizations(self, document_id: str, user_id: str, immunizations: list):
        """Save normalized immunizations."""
        for imm in immunizations:
            immunization = ClinicalImmunization(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=user_id,
                vaccine_name=imm.get("vaccine_name"),
                administration_date=self._parse_date(imm.get("administration_date")),
                dose_number=imm.get("dose_number"),
                site=imm.get("site"),
                route=imm.get("route"),
                lot_number=imm.get("lot_number"),
                expiration_date=self._parse_date(imm.get("expiration_date")),
                manufacturer=imm.get("manufacturer"),
                administered_by=imm.get("administered_by"),
                facility=imm.get("facility"),
                notes=imm.get("notes"),
            )
            self.db.add(immunization)

    def _save_timeline_events(
        self,
        document_id: str,
        user_id: str,
        agent_context: Dict,
        clinical_data: Dict,
        validation: Dict = None,
    ):
        """
        Save timeline events from agent context with smart entity linking.
        Uses document_date as fallback when event date is missing.
        """
        temporal_events = agent_context.get("temporal_events", [])

        # Extract document_date from validation metadata as fallback
        document_date = None
        if validation:
            doc_metadata = validation.get("document_metadata", {})
            doc_date_str = doc_metadata.get("document_date")
            if doc_date_str:
                document_date = self._parse_datetime(doc_date_str)

        for event in temporal_events:
            # Parse event date, fallback to document date
            event_date = self._parse_datetime(event.get("date"))
            if not event_date and document_date:
                event_date = document_date

            # Skip events without any valid date
            if not event_date:
                print(
                    f"  ⚠️  Skipping timeline event '{event.get('event_title', 'Unknown')}' - no date available"
                )
                continue
            # Link to related entities if mentioned
            related_entity = event.get("related_entity", "").lower()
            related_condition_id = None
            related_medication_id = None
            related_procedure_id = None
            related_lab_result_id = None

            # Try to link medications
            if event.get("event_type") in [
                "medication_started",
                "medication_stopped",
                "medication",
            ]:
                for med in clinical_data.get("medications", []):
                    if related_entity and related_entity in med.get("name", "").lower():
                        related_medication_id = self._find_saved_entity_id(
                            ClinicalMedication, document_id, "name", med.get("name")
                        )
                        break

            # Try to link conditions
            elif event.get("event_type") in ["diagnosis", "condition"]:
                for cond in clinical_data.get("conditions", []):
                    if (
                        related_entity
                        and related_entity in cond.get("name", "").lower()
                    ):
                        related_condition_id = self._find_saved_entity_id(
                            ClinicalCondition, document_id, "name", cond.get("name")
                        )
                        break

            # Try to link lab results
            elif event.get("event_type") in ["lab_result", "lab"]:
                for lab in clinical_data.get("lab_results", []):
                    if (
                        related_entity
                        and related_entity in lab.get("test_name", "").lower()
                    ):
                        related_lab_result_id = self._find_saved_entity_id(
                            ClinicalLabResult,
                            document_id,
                            "test_name",
                            lab.get("test_name"),
                        )
                        break

            # Try to link procedures
            elif event.get("event_type") in ["procedure", "surgery"]:
                for proc in clinical_data.get("procedures", []):
                    if (
                        related_entity
                        and related_entity in proc.get("procedure_name", "").lower()
                    ):
                        related_procedure_id = self._find_saved_entity_id(
                            ClinicalProcedure,
                            document_id,
                            "procedure_name",
                            proc.get("procedure_name"),
                        )
                        break

            timeline_event = TimelineEvent(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=user_id,
                event_date=event_date,  # Now guaranteed to be non-null
                event_type=event.get("event_type", "other"),
                event_title=event.get("event_title", "Unknown Event"),
                event_description=event.get("event_description"),
                importance=event.get("importance", "medium"),
                provider=event.get("provider"),
                facility=event.get("facility"),
                related_condition_id=related_condition_id,
                related_medication_id=related_medication_id,
                related_procedure_id=related_procedure_id,
                related_lab_result_id=related_lab_result_id,
            )
            self.db.add(timeline_event)

    def _save_search_terms(self, document_id: str, agent_context: Dict):
        """Save search terms from agent context."""
        keywords = agent_context.get("semantic_keywords", [])

        for keyword in keywords:
            if isinstance(keyword, dict):
                term = keyword.get("term")
                term_type = keyword.get("type")
            else:
                term = str(keyword)
                term_type = None

            if term:
                search_term = SearchTerm(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    term=term,
                    term_type=term_type,
                )
                self.db.add(search_term)

    def _log_audit(self, user_id: str, document_id: str, action: str, description: str):
        """Log audit trail."""
        audit_log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            document_id=document_id,
            action=action,
            entity_type="document",
            entity_id=document_id,
            changes={"description": description},
            timestamp=datetime.utcnow(),
        )
        self.db.add(audit_log)

    def _find_saved_entity_id(
        self, model_class, document_id: str, field_name: str, field_value: str
    ) -> Optional[str]:
        """Find saved entity ID by document_id and field value."""
        try:
            entity = (
                self.db.query(model_class)
                .filter(
                    getattr(model_class, "document_id") == document_id,
                    getattr(model_class, field_name) == field_value,
                    getattr(model_class, "deleted_at").is_(None),
                )
                .first()
            )
            return entity.id if entity else None
        except Exception:
            return None

    def _parse_date(self, date_str: Optional[str]):
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            from dateutil import parser

            return parser.parse(date_str).date()
        except:
            return None

    def _parse_datetime(self, datetime_str: Optional[str]):
        """Parse datetime string to datetime object."""
        if not datetime_str:
            return None
        try:
            from dateutil import parser

            return parser.parse(datetime_str)
        except:
            return None
