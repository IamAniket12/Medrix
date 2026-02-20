"""Timeline Intelligence Service - Smart event linking and insights."""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

from ..models import (
    TimelineEvent,
    ClinicalCondition,
    ClinicalMedication,
    ClinicalLabResult,
    ClinicalProcedure,
)


class TimelineIntelligenceService:
    """
    Provides intelligent analysis and linking of timeline events.

    This service:
    1. Links related events (diagnosis → treatment → outcome)
    2. Detects patterns (medication adherence, disease progression)
    3. Generates insights and predictions
    4. Creates smart reminders
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # EVENT LINKING
    # ============================================================

    def link_diagnosis_to_treatments(self, user_id: str) -> Dict[str, List[str]]:
        """
        Link diagnosis events to subsequent treatment events.

        Logic:
        - Find diagnosis events
        - Find medications started after diagnosis with matching condition
        - Link them together

        Returns: Dict of {diagnosis_event_id: [treatment_event_ids]}
        """
        # Get all diagnosis events
        diagnoses = (
            self.db.query(TimelineEvent)
            .filter(
                TimelineEvent.user_id == user_id,
                TimelineEvent.event_type == "diagnosis",
                TimelineEvent.deleted_at.is_(None),
            )
            .all()
        )

        links = {}

        for diagnosis in diagnoses:
            # Find medications started after this diagnosis
            related_meds = (
                self.db.query(TimelineEvent)
                .filter(
                    TimelineEvent.user_id == user_id,
                    TimelineEvent.event_type == "medication_started",
                    TimelineEvent.event_date >= diagnosis.event_date,
                    TimelineEvent.deleted_at.is_(None),
                )
                .all()
            )

            # Smart matching: Check if medication indication matches diagnosis
            if diagnosis.related_condition_id:
                condition = (
                    self.db.query(ClinicalCondition)
                    .filter(ClinicalCondition.id == diagnosis.related_condition_id)
                    .first()
                )

                if condition:
                    condition_keywords = condition.name.lower().split()

                    for med_event in related_meds:
                        if med_event.related_medication_id:
                            med = (
                                self.db.query(ClinicalMedication)
                                .filter(
                                    ClinicalMedication.id
                                    == med_event.related_medication_id
                                )
                                .first()
                            )

                            if med and med.indication:
                                # Check if indication mentions the condition
                                indication_lower = med.indication.lower()
                                if any(
                                    kw in indication_lower for kw in condition_keywords
                                ):
                                    if diagnosis.id not in links:
                                        links[diagnosis.id] = []
                                    links[diagnosis.id].append(med_event.id)

        return links

    def link_abnormal_labs_to_followups(self, user_id: str) -> Dict[str, List[str]]:
        """
        Link abnormal lab results to follow-up labs of the same test.

        Returns: Dict of {initial_lab_event_id: [followup_lab_event_ids]}
        """
        # Get all lab result events
        lab_events = (
            self.db.query(TimelineEvent)
            .filter(
                TimelineEvent.user_id == user_id,
                TimelineEvent.event_type == "lab_result",
                TimelineEvent.deleted_at.is_(None),
            )
            .order_by(TimelineEvent.event_date)
            .all()
        )

        links = {}

        for i, lab_event in enumerate(lab_events):
            if lab_event.related_lab_result_id:
                lab = (
                    self.db.query(ClinicalLabResult)
                    .filter(ClinicalLabResult.id == lab_event.related_lab_result_id)
                    .first()
                )

                if lab and lab.is_abnormal:
                    # Find subsequent labs of same test
                    followups = []
                    for j in range(i + 1, len(lab_events)):
                        followup_event = lab_events[j]
                        if followup_event.related_lab_result_id:
                            followup_lab = (
                                self.db.query(ClinicalLabResult)
                                .filter(
                                    ClinicalLabResult.id
                                    == followup_event.related_lab_result_id
                                )
                                .first()
                            )

                            if followup_lab and followup_lab.test_name == lab.test_name:
                                # This is a follow-up of the same test
                                followups.append(followup_event.id)

                    if followups:
                        links[lab_event.id] = followups

        return links

    def link_procedures_to_recoveries(self, user_id: str) -> Dict[str, List[str]]:
        """
        Link procedure events to post-procedure visits/checkups.

        Returns: Dict of {procedure_event_id: [recovery_event_ids]}
        """
        # Get all procedure events
        procedures = (
            self.db.query(TimelineEvent)
            .filter(
                TimelineEvent.user_id == user_id,
                TimelineEvent.event_type == "procedure",
                TimelineEvent.deleted_at.is_(None),
            )
            .all()
        )

        links = {}

        for procedure in procedures:
            # Find visits within 30 days after procedure
            followup_window_end = procedure.event_date + timedelta(days=30)

            recovery_visits = (
                self.db.query(TimelineEvent)
                .filter(
                    TimelineEvent.user_id == user_id,
                    TimelineEvent.event_type.in_(["visit", "checkup"]),
                    TimelineEvent.event_date > procedure.event_date,
                    TimelineEvent.event_date <= followup_window_end,
                    TimelineEvent.deleted_at.is_(None),
                )
                .all()
            )

            if recovery_visits:
                links[procedure.id] = [v.id for v in recovery_visits]

        return links

    # ============================================================
    # PATTERN DETECTION
    # ============================================================

    def detect_medication_adherence_gaps(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Detect potential medication non-adherence.

        Logic:
        - Find medications started
        - Check if there's a "medication stopped" or refill event within expected timeframe
        - Flag gaps as potential non-adherence

        Returns: List of alerts
        """
        alerts = []

        # Get active medications (started but not stopped)
        started_meds = (
            self.db.query(TimelineEvent)
            .filter(
                TimelineEvent.user_id == user_id,
                TimelineEvent.event_type == "medication_started",
                TimelineEvent.deleted_at.is_(None),
            )
            .all()
        )

        for med_event in started_meds:
            # Check if there's a corresponding "stopped" event
            stopped_event = (
                self.db.query(TimelineEvent)
                .filter(
                    TimelineEvent.user_id == user_id,
                    TimelineEvent.event_type == "medication_stopped",
                    TimelineEvent.related_medication_id
                    == med_event.related_medication_id,
                    TimelineEvent.deleted_at.is_(None),
                )
                .first()
            )

            if not stopped_event:
                # Medication appears to be active
                # Check if it's been > 60 days since start (typical prescription duration)
                if not med_event.event_date:
                    continue
                days_since_start = (datetime.utcnow() - med_event.event_date).days

                if days_since_start > 60:
                    alerts.append(
                        {
                            "type": "medication_adherence",
                            "severity": "medium",
                            "event_id": med_event.id,
                            "message": f"No refill recorded for {med_event.event_title} in {days_since_start} days",
                            "recommendation": "Check medication adherence or update status",
                        }
                    )

        return alerts

    def detect_disease_progression(
        self, user_id: str, condition_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze lab results to detect disease progression/improvement.

        Example: Track HbA1c for diabetes, PSA for prostate health, etc.

        Returns: Progression analysis or None
        """
        # Find condition
        condition = (
            self.db.query(ClinicalCondition)
            .filter(
                ClinicalCondition.user_id == user_id,
                ClinicalCondition.name.ilike(f"%{condition_name}%"),
                ClinicalCondition.deleted_at.is_(None),
            )
            .first()
        )

        if not condition:
            return None

        # Map conditions to relevant lab tests
        condition_lab_map = {
            "diabetes": ["HbA1c", "Glucose", "Fasting Glucose"],
            "hypertension": ["Blood Pressure"],
            "hyperlipidemia": ["Cholesterol", "LDL", "HDL", "Triglycerides"],
            "kidney": ["Creatinine", "eGFR", "BUN"],
            "liver": ["ALT", "AST", "Bilirubin"],
        }

        relevant_tests = []
        for key, tests in condition_lab_map.items():
            if key in condition.name.lower():
                relevant_tests = tests
                break

        if not relevant_tests:
            return None

        # Get lab results for these tests
        labs = []
        for test_name in relevant_tests:
            test_results = (
                self.db.query(ClinicalLabResult)
                .filter(
                    ClinicalLabResult.user_id == user_id,
                    ClinicalLabResult.test_name.ilike(f"%{test_name}%"),
                    ClinicalLabResult.deleted_at.is_(None),
                )
                .order_by(ClinicalLabResult.test_date)
                .all()
            )
            labs.extend(test_results)

        if len(labs) < 2:
            return None  # Need at least 2 data points for trend

        # Simple trend analysis: compare first and last
        first_result = labs[0]
        last_result = labs[-1]

        try:
            first_value = float(first_result.value)
            last_value = float(last_result.value)

            change_percent = ((last_value - first_value) / first_value) * 100

            trend = "stable"
            if abs(change_percent) > 10:
                trend = "improving" if change_percent < 0 else "worsening"

            return {
                "condition": condition.name,
                "test_name": first_result.test_name,
                "first_value": f"{first_value} {first_result.unit}",
                "first_date": first_result.test_date.isoformat(),
                "last_value": f"{last_value} {last_result.unit}",
                "last_date": last_result.test_date.isoformat(),
                "change_percent": round(change_percent, 1),
                "trend": trend,
                "recommendation": self._get_trend_recommendation(trend, condition.name),
            }

        except (ValueError, TypeError):
            return None

    def _get_trend_recommendation(self, trend: str, condition: str) -> str:
        """Get recommendation based on trend."""
        if trend == "improving":
            return f"Great progress! Continue current treatment plan for {condition}."
        elif trend == "worsening":
            return f"Consider consulting your doctor about {condition} management."
        else:
            return f"{condition} appears stable. Continue monitoring."

    # ============================================================
    # PREDICTIONS & REMINDERS
    # ============================================================

    def predict_upcoming_events(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Predict upcoming health events based on historical patterns.

        Examples:
        - Annual checkup due
        - Lab work due (e.g., HbA1c every 3 months)
        - Medication refill needed
        - Screening due based on age
        """
        predictions = []

        # 1. Check for overdue annual checkup
        last_checkup = (
            self.db.query(TimelineEvent)
            .filter(
                TimelineEvent.user_id == user_id,
                TimelineEvent.event_type == "visit",
                TimelineEvent.deleted_at.is_(None),
            )
            .order_by(TimelineEvent.event_date.desc())
            .first()
        )

        if last_checkup and last_checkup.event_date:
            days_since_checkup = (datetime.utcnow() - last_checkup.event_date).days
            if days_since_checkup > 365:
                predictions.append(
                    {
                        "type": "checkup_due",
                        "priority": "high",
                        "message": f"Annual checkup overdue by {days_since_checkup - 365} days",
                        "recommended_action": "Schedule annual physical examination",
                        "suggested_date": datetime.utcnow() + timedelta(days=14),
                    }
                )

        # 2. Check for lab work patterns
        # If patient has diabetes, suggest quarterly HbA1c
        diabetes = (
            self.db.query(ClinicalCondition)
            .filter(
                ClinicalCondition.user_id == user_id,
                ClinicalCondition.name.ilike("%diabetes%"),
                ClinicalCondition.status == "active",
                ClinicalCondition.deleted_at.is_(None),
            )
            .first()
        )

        if diabetes:
            last_hba1c = (
                self.db.query(ClinicalLabResult)
                .filter(
                    ClinicalLabResult.user_id == user_id,
                    ClinicalLabResult.test_name.ilike("%HbA1c%"),
                    ClinicalLabResult.deleted_at.is_(None),
                )
                .order_by(ClinicalLabResult.test_date.desc())
                .first()
            )

            if last_hba1c and last_hba1c.test_date:
                days_since_test = (datetime.utcnow() - last_hba1c.test_date).days
                if days_since_test > 90:  # 3 months
                    predictions.append(
                        {
                            "type": "lab_due",
                            "priority": "medium",
                            "message": f"HbA1c test due (last: {days_since_test} days ago)",
                            "recommended_action": "Schedule HbA1c test with your doctor",
                            "suggested_date": datetime.utcnow() + timedelta(days=7),
                        }
                    )

        return predictions

    def generate_health_score(self, user_id: str) -> Dict[str, Any]:
        """
        Generate an overall health score based on timeline analysis.

        Factors:
        - Medication adherence
        - Regular checkups
        - Lab result trends
        - Condition management

        Returns: Score (0-100) with breakdown
        """
        scores = {}

        # 1. Medication Adherence (30 points)
        adherence_alerts = self.detect_medication_adherence_gaps(user_id)
        active_meds = (
            self.db.query(ClinicalMedication)
            .filter(
                ClinicalMedication.user_id == user_id,
                ClinicalMedication.is_active == True,
                ClinicalMedication.deleted_at.is_(None),
            )
            .count()
        )

        if active_meds > 0:
            adherence_rate = max(0, active_meds - len(adherence_alerts)) / active_meds
            scores["medication_adherence"] = round(adherence_rate * 30)
        else:
            scores["medication_adherence"] = 30  # No meds = full points

        # 2. Regular Checkups (20 points)
        recent_visits = (
            self.db.query(TimelineEvent)
            .filter(
                TimelineEvent.user_id == user_id,
                TimelineEvent.event_type == "visit",
                TimelineEvent.event_date >= datetime.utcnow() - timedelta(days=365),
                TimelineEvent.deleted_at.is_(None),
            )
            .count()
        )

        scores["regular_checkups"] = min(20, recent_visits * 10)

        # 3. Lab Monitoring (20 points)
        recent_labs = (
            self.db.query(ClinicalLabResult)
            .filter(
                ClinicalLabResult.user_id == user_id,
                ClinicalLabResult.test_date >= datetime.utcnow() - timedelta(days=180),
                ClinicalLabResult.deleted_at.is_(None),
            )
            .count()
        )

        scores["lab_monitoring"] = min(20, recent_labs * 4)

        # 4. Condition Management (30 points)
        active_conditions = (
            self.db.query(ClinicalCondition)
            .filter(
                ClinicalCondition.user_id == user_id,
                ClinicalCondition.status == "active",
                ClinicalCondition.deleted_at.is_(None),
            )
            .count()
        )

        if active_conditions == 0:
            scores["condition_management"] = 30
        else:
            # Simplified: assume each condition needs 1 medication
            medications_for_conditions = min(active_conditions, active_meds)
            management_rate = medications_for_conditions / active_conditions
            scores["condition_management"] = round(management_rate * 30)

        total_score = sum(scores.values())

        # Determine grade
        if total_score >= 90:
            grade = "A"
        elif total_score >= 80:
            grade = "B"
        elif total_score >= 70:
            grade = "C"
        elif total_score >= 60:
            grade = "D"
        else:
            grade = "F"

        return {
            "total_score": total_score,
            "grade": grade,
            "breakdown": scores,
            "insights": self._generate_score_insights(scores),
        }

    def _generate_score_insights(self, scores: Dict[str, int]) -> List[str]:
        """Generate actionable insights based on scores."""
        insights = []

        if scores["medication_adherence"] < 20:
            insights.append("🔴 Medication adherence needs attention")
        else:
            insights.append("✅ Great medication adherence!")

        if scores["regular_checkups"] < 15:
            insights.append("🔴 Schedule regular checkups with your doctor")
        else:
            insights.append("✅ Keeping up with regular checkups!")

        if scores["lab_monitoring"] < 15:
            insights.append("🔴 Consider more regular lab work")

        return insights
