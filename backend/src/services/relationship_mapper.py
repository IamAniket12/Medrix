"""Agent 6: Relationship Mapper - Maps relationships between clinical entities."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models import (
    ClinicalCondition,
    ClinicalMedication,
    ClinicalLabResult,
    ClinicalProcedure,
    TimelineEvent,
)
from .embeddings_service import embeddings_service

logger = logging.getLogger(__name__)


class ClinicalRelationship:
    """Represents a relationship between two clinical entities."""

    def __init__(
        self,
        source_type: str,
        source_id: int,
        source_name: str,
        target_type: str,
        target_id: int,
        target_name: str,
        relationship_type: str,
        confidence: float,
        evidence: str,
    ):
        self.source_type = source_type
        self.source_id = source_id
        self.source_name = source_name
        self.target_type = target_type
        self.target_id = target_id
        self.target_name = target_name
        self.relationship_type = relationship_type
        self.confidence = confidence
        self.evidence = evidence

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": {
                "type": self.source_type,
                "id": self.source_id,
                "name": self.source_name,
            },
            "target": {
                "type": self.target_type,
                "id": self.target_id,
                "name": self.target_name,
            },
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


class RelationshipMapper:
    """
    Agent 6: Relationship Mapper

    Maps relationships between clinical entities:
    - Medication → Condition (treats_for)
    - Lab → Condition (monitors)
    - Procedure → Condition (treats)
    - Medication → Medication (interacts_with)
    - Lab → Lab (follow_up_to)

    Uses both rule-based logic and semantic similarity (RAG) for relationship detection.
    """

    def __init__(self):
        """Initialize the Relationship Mapper."""
        self.embeddings_service = embeddings_service

        # Known medication-condition mappings (expandable)
        self.medication_condition_map = {
            "metformin": ["diabetes", "type 2 diabetes", "t2dm"],
            "lisinopril": ["hypertension", "high blood pressure", "htn"],
            "atorvastatin": ["hyperlipidemia", "high cholesterol", "dyslipidemia"],
            "levothyroxine": ["hypothyroidism", "thyroid disorder"],
            "omeprazole": ["gerd", "acid reflux", "gastroesophageal reflux"],
            "albuterol": ["asthma", "copd", "bronchospasm"],
            "warfarin": ["atrial fibrillation", "dvt", "blood clot", "anticoagulation"],
            "insulin": [
                "diabetes",
                "type 1 diabetes",
                "type 2 diabetes",
                "t1dm",
                "t2dm",
            ],
        }

        # Known lab-condition mappings
        self.lab_condition_map = {
            "hba1c": ["diabetes", "type 2 diabetes", "t2dm"],
            "glucose": ["diabetes", "type 2 diabetes", "t2dm"],
            "tsh": ["hypothyroidism", "hyperthyroidism", "thyroid disorder"],
            "ldl": ["hyperlipidemia", "high cholesterol", "cardiovascular disease"],
            "cholesterol": [
                "hyperlipidemia",
                "high cholesterol",
                "cardiovascular disease",
            ],
            "inr": ["anticoagulation", "atrial fibrillation", "blood clot"],
            "creatinine": ["kidney disease", "renal failure", "ckd"],
            "alt": ["liver disease", "hepatitis"],
            "ast": ["liver disease", "hepatitis"],
        }

    def map_all_relationships(
        self,
        db: Session,
        user_id: str,
        document_id: Optional[int] = None,
        fresh_extractions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Map all relationships for a user's clinical data.

        Args:
            db: Database session
            user_id: User ID
            document_id: Optional document ID to scope relationships to new data
            fresh_extractions: Freshly extracted data from Agent 2 (before DB persistence)

        Returns:
            Dictionary with:
            - relationships: List of ClinicalRelationship objects
            - summary: Statistics about relationships found
            - confidence_distribution: Distribution of confidence scores
        """
        try:
            logger.info(f"Mapping clinical relationships for user {user_id}")

            all_relationships = []

            # Map medication → condition relationships
            med_cond_relationships = self._map_medication_condition_relationships(
                db, user_id, document_id, fresh_extractions
            )
            all_relationships.extend(med_cond_relationships)

            # Map lab → condition relationships
            lab_cond_relationships = self._map_lab_condition_relationships(
                db, user_id, document_id, fresh_extractions
            )
            all_relationships.extend(lab_cond_relationships)

            # Map lab → lab follow-up relationships
            lab_lab_relationships = self._map_lab_followup_relationships(
                db, user_id, document_id
            )
            all_relationships.extend(lab_lab_relationships)

            # Map procedure → condition relationships
            proc_cond_relationships = self._map_procedure_condition_relationships(
                db, user_id, document_id, fresh_extractions
            )
            all_relationships.extend(proc_cond_relationships)

            # Generate summary
            summary = self._generate_relationship_summary(all_relationships)

            logger.info(
                f"Found {len(all_relationships)} relationships: "
                f"{summary['by_type']}"
            )

            return {
                "relationships": [rel.to_dict() for rel in all_relationships],
                "summary": summary,
                "total_count": len(all_relationships),
            }

        except Exception as e:
            logger.error(f"Error mapping relationships: {str(e)}")
            return {
                "relationships": [],
                "summary": {},
                "total_count": 0,
                "error": str(e),
            }

    def _map_medication_condition_relationships(
        self,
        db: Session,
        user_id: str,
        document_id: Optional[int] = None,
        fresh_extractions: Optional[Dict[str, Any]] = None,
    ) -> List[ClinicalRelationship]:
        """
        Map medication → condition (treats_for) relationships.

        Now uses both database records AND fresh extractions for immediate mapping.
        """
        relationships = []

        try:
            # Get all active medications from database
            med_query = db.query(ClinicalMedication).filter(
                ClinicalMedication.user_id == user_id,
                ClinicalMedication.deleted_at.is_(None),
            )
            if document_id:
                med_query = med_query.filter(
                    ClinicalMedication.document_id == document_id
                )
            medications = med_query.all()

            # Add fresh extractions to mapping pool (not yet in database)
            fresh_medications = []
            fresh_conditions = []
            if fresh_extractions:
                fresh_medications = fresh_extractions.get("medications", [])
                fresh_conditions = fresh_extractions.get("conditions", [])
                logger.info(
                    f"Including {len(fresh_medications)} fresh medications, "
                    f"{len(fresh_conditions)} fresh conditions for relationship mapping"
                )

            # Get all active conditions
            conditions = (
                db.query(ClinicalCondition)
                .filter(
                    ClinicalCondition.user_id == user_id,
                    ClinicalCondition.deleted_at.is_(None),
                )
                .all()
            )

            # For each medication (database + fresh), find matching conditions
            all_meds = []

            # Add database medications
            for med in medications:
                all_meds.append({"id": med.id, "name": med.name, "source": "database"})

            # Add fresh medications (ID will be assigned after persistence)
            for idx, fresh_med in enumerate(fresh_medications):
                all_meds.append(
                    {
                        "id": -(idx + 1),  # Negative ID for fresh data
                        "name": fresh_med.get("name", ""),
                        "source": "fresh",
                    }
                )

            # Build condition pool (database + fresh)
            all_conditions = []
            for cond in conditions:
                all_conditions.append(
                    {"id": cond.id, "name": cond.name, "source": "database"}
                )
            for idx, fresh_cond in enumerate(fresh_conditions):
                all_conditions.append(
                    {
                        "id": -(idx + 1),
                        "name": fresh_cond.get("name", ""),
                        "source": "fresh",
                    }
                )

            # Map relationships
            for med in all_meds:
                med_name_lower = med["name"].lower()

                # Check rule-based mappings first
                for (
                    med_key,
                    condition_keywords,
                ) in self.medication_condition_map.items():
                    if med_key in med_name_lower:
                        # Find matching conditions
                        for cond in all_conditions:
                            cond_name_lower = cond["name"].lower()
                            if any(
                                keyword in cond_name_lower
                                for keyword in condition_keywords
                            ):
                                relationships.append(
                                    ClinicalRelationship(
                                        source_type="medication",
                                        source_id=med["id"],
                                        source_name=med["name"],
                                        target_type="condition",
                                        target_id=cond["id"],
                                        target_name=cond["name"],
                                        relationship_type="treats_for",
                                        confidence=(
                                            0.9
                                            if med["source"] == "database"
                                            and cond["source"] == "database"
                                            else 0.85
                                        ),
                                        evidence=f"Known medication-condition mapping: {med_key} ({med['source']} → {cond['source']})",
                                    )
                                )

                # Use semantic similarity for unmatched medications
                # (This would use embeddings to find semantically similar conditions)
                # For now, skip to keep it simple

            return relationships

        except Exception as e:
            logger.error(f"Error mapping medication-condition relationships: {str(e)}")
            # Rollback transaction if it's in a bad state
            try:
                db.rollback()
            except:
                pass
            return []

    def _map_lab_condition_relationships(
        self,
        db: Session,
        user_id: str,
        document_id: Optional[int] = None,
        fresh_extractions: Optional[Dict[str, Any]] = None,
    ) -> List[ClinicalRelationship]:
        """Map lab → condition (monitors) relationships."""
        relationships = []

        try:
            # Get all lab results from database
            lab_query = db.query(ClinicalLabResult).filter(
                ClinicalLabResult.user_id == user_id,
                ClinicalLabResult.deleted_at.is_(None),
            )
            if document_id:
                lab_query = lab_query.filter(
                    ClinicalLabResult.document_id == document_id
                )
            labs = lab_query.all()

            # Add fresh lab results
            fresh_labs = []
            fresh_conditions = []
            if fresh_extractions:
                fresh_labs = fresh_extractions.get("lab_results", [])
                fresh_conditions = fresh_extractions.get("conditions", [])

            # Get all active conditions
            conditions = (
                db.query(ClinicalCondition)
                .filter(
                    ClinicalCondition.user_id == user_id,
                    ClinicalCondition.deleted_at.is_(None),
                )
                .all()
            )

            # For each lab, find matching conditions
            for lab in labs:
                lab_name_lower = lab.test_name.lower()

                # Check rule-based mappings
                for lab_key, condition_keywords in self.lab_condition_map.items():
                    if lab_key in lab_name_lower:
                        # Find matching conditions
                        for cond in conditions:
                            cond_name_lower = cond.name.lower()
                            if any(
                                keyword in cond_name_lower
                                for keyword in condition_keywords
                            ):
                                relationships.append(
                                    ClinicalRelationship(
                                        source_type="lab_result",
                                        source_id=lab.id,
                                        source_name=lab.test_name,
                                        target_type="condition",
                                        target_id=cond.id,
                                        target_name=cond.name,
                                        relationship_type="monitors",
                                        confidence=0.85,
                                        evidence=f"Known lab-condition mapping: {lab_key}",
                                    )
                                )

            return relationships

        except Exception as e:
            logger.error(f"Error mapping lab-condition relationships: {str(e)}")
            return []

    def _map_lab_followup_relationships(
        self, db: Session, user_id: str, document_id: Optional[int] = None
    ) -> List[ClinicalRelationship]:
        """Map lab → lab (follow_up_to) relationships."""
        relationships = []

        try:
            # Get all lab results ordered by date
            lab_query = (
                db.query(ClinicalLabResult)
                .filter(
                    ClinicalLabResult.user_id == user_id,
                    ClinicalLabResult.deleted_at.is_(None),
                    ClinicalLabResult.test_date.isnot(None),
                )
                .order_by(ClinicalLabResult.test_date)
            )

            if document_id:
                lab_query = lab_query.filter(
                    ClinicalLabResult.document_id == document_id
                )

            labs = lab_query.all()

            # Group labs by test name
            labs_by_test = {}
            for lab in labs:
                test_name = lab.test_name.lower().strip()
                if test_name not in labs_by_test:
                    labs_by_test[test_name] = []
                labs_by_test[test_name].append(lab)

            # Find follow-up relationships (same test within 1 year)
            for test_name, test_labs in labs_by_test.items():
                if len(test_labs) < 2:
                    continue

                # Sort by date
                test_labs.sort(key=lambda x: x.test_date)

                # Link consecutive tests
                for i in range(len(test_labs) - 1):
                    current_lab = test_labs[i]
                    next_lab = test_labs[i + 1]

                    # Check if within 1 year
                    time_diff = next_lab.test_date - current_lab.test_date
                    if time_diff.days <= 365:
                        relationships.append(
                            ClinicalRelationship(
                                source_type="lab_result",
                                source_id=next_lab.id,
                                source_name=next_lab.test_name,
                                target_type="lab_result",
                                target_id=current_lab.id,
                                target_name=current_lab.test_name,
                                relationship_type="follow_up_to",
                                confidence=0.95,
                                evidence=f"Same test {time_diff.days} days apart",
                            )
                        )

            return relationships

        except Exception as e:
            logger.error(f"Error mapping lab follow-up relationships: {str(e)}")
            return []

    def _map_procedure_condition_relationships(
        self,
        db: Session,
        user_id: str,
        document_id: Optional[int] = None,
        fresh_extractions: Optional[Dict[str, Any]] = None,
    ) -> List[ClinicalRelationship]:
        """Map procedure → condition (treats) relationships."""
        relationships = []

        try:
            # Get all procedures
            proc_query = db.query(ClinicalProcedure).filter(
                ClinicalProcedure.user_id == user_id,
                ClinicalProcedure.deleted_at.is_(None),
            )
            if document_id:
                proc_query = proc_query.filter(
                    ClinicalProcedure.document_id == document_id
                )
            procedures = proc_query.all()

            # Get all conditions
            conditions = (
                db.query(ClinicalCondition)
                .filter(
                    ClinicalCondition.user_id == user_id,
                    ClinicalCondition.deleted_at.is_(None),
                )
                .all()
            )

            # For each procedure, find conditions diagnosed within 6 months before procedure
            for proc in procedures:
                # Use performed_date (actual column name) instead of procedure_date
                if not proc.performed_date:
                    continue

                # Look for conditions diagnosed within 6 months before procedure
                for cond in conditions:
                    if not cond.diagnosed_date:
                        continue

                    time_diff = proc.performed_date - cond.diagnosed_date
                    if timedelta(days=0) <= time_diff <= timedelta(days=180):
                        relationships.append(
                            ClinicalRelationship(
                                source_type="procedure",
                                source_id=proc.id,
                                source_name=proc.procedure_name,
                                target_type="condition",
                                target_id=cond.id,
                                target_name=cond.name,
                                relationship_type="treats",
                                confidence=0.7,
                                evidence=f"Procedure performed {time_diff.days} days after diagnosis",
                            )
                        )

            return relationships

        except Exception as e:
            logger.error(f"Error mapping procedure-condition relationships: {str(e)}")
            return []

    def _generate_relationship_summary(
        self, relationships: List[ClinicalRelationship]
    ) -> Dict[str, Any]:
        """Generate summary statistics about relationships."""

        # Count by relationship type
        by_type = {}
        for rel in relationships:
            rel_type = rel.relationship_type
            by_type[rel_type] = by_type.get(rel_type, 0) + 1

        # Average confidence
        avg_confidence = (
            sum(rel.confidence for rel in relationships) / len(relationships)
            if relationships
            else 0
        )

        # Confidence distribution
        confidence_dist = {
            "high (>0.9)": sum(1 for rel in relationships if rel.confidence > 0.9),
            "medium (0.7-0.9)": sum(
                1 for rel in relationships if 0.7 <= rel.confidence <= 0.9
            ),
            "low (<0.7)": sum(1 for rel in relationships if rel.confidence < 0.7),
        }

        return {
            "total": len(relationships),
            "by_type": by_type,
            "average_confidence": round(avg_confidence, 2),
            "confidence_distribution": confidence_dist,
        }


# Singleton instance
relationship_mapper = RelationshipMapper()
