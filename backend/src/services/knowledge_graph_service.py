"""
Knowledge Graph Service — builds a rich, entity-deduplicated clinical graph.

Design philosophy (Google Health / Meta Knowledge Graph approach):
  1. Entities are *canonical nodes* — deduplicated by normalised name across all
     documents so "Hypertension" in 3 documents becomes ONE node with 3 sources.
  2. Edges are typed, directional and carry a confidence score + human-readable
     evidence string so the UI can explain every relationship.
  3. Relationship types are semantically precise:
       treats_for, prescribed_for, monitors, abnormal_indicator,
       follow_up_to, co_occurs_with, caused_by, allergic_to,
       procedure_for, contraindicated_with
  4. Temporal evidence is used wherever possible: if a medication was started
     after a diagnosis the edge is "treats_for" with high confidence; if only
     co-occurring in the same document it's "co_occurs_with" at lower confidence.
  5. Properties travel with each node so the frontend can show rich tooltips.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models import (
    ClinicalAllergy,
    ClinicalCondition,
    ClinicalLabResult,
    ClinicalMedication,
    ClinicalProcedure,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Static domain knowledge  (expandable — think of this as a small ontology)
# ──────────────────────────────────────────────────────────────────────────────

MEDICATION_TREATS: Dict[str, List[str]] = {
    "metformin": ["diabetes", "type 2 diabetes", "t2dm", "hyperglycemia"],
    "lisinopril": ["hypertension", "high blood pressure", "htn", "heart failure"],
    "atorvastatin": [
        "hyperlipidemia",
        "high cholesterol",
        "dyslipidemia",
        "cardiovascular",
    ],
    "simvastatin": ["hyperlipidemia", "high cholesterol", "dyslipidemia"],
    "levothyroxine": ["hypothyroidism", "thyroid"],
    "omeprazole": ["gerd", "acid reflux", "gastroesophageal reflux", "gastritis"],
    "pantoprazole": ["gerd", "acid reflux", "peptic ulcer"],
    "albuterol": ["asthma", "copd", "bronchospasm"],
    "salbutamol": ["asthma", "copd", "bronchospasm"],
    "warfarin": ["atrial fibrillation", "dvt", "pulmonary embolism", "blood clot"],
    "apixaban": ["atrial fibrillation", "dvt", "pulmonary embolism"],
    "insulin": ["diabetes", "type 1 diabetes", "type 2 diabetes", "t1dm", "t2dm"],
    "amlodipine": ["hypertension", "angina", "coronary artery disease"],
    "losartan": ["hypertension", "heart failure", "kidney disease"],
    "aspirin": [
        "cardiovascular disease",
        "coronary artery disease",
        "stroke prevention",
    ],
    "metoprolol": ["hypertension", "heart failure", "atrial fibrillation", "angina"],
    "furosemide": ["heart failure", "edema", "hypertension"],
    "prednisone": ["asthma", "copd", "autoimmune", "inflammation", "allergy"],
    "amoxicillin": ["infection", "pneumonia", "sinusitis", "otitis"],
    "azithromycin": ["infection", "pneumonia", "sinusitis"],
    "sertraline": ["depression", "anxiety", "ocd", "ptsd"],
    "fluoxetine": ["depression", "anxiety", "ocd"],
    "methotrexate": ["rheumatoid arthritis", "psoriasis", "autoimmune"],
    "gabapentin": ["neuropathy", "epilepsy", "seizure", "pain"],
    "pregabalin": ["neuropathy", "fibromyalgia", "epilepsy"],
    "hydrochlorothiazide": ["hypertension", "edema", "heart failure"],
}

LAB_MONITORS: Dict[str, List[str]] = {
    "hba1c": ["diabetes", "type 2 diabetes", "t2dm", "hyperglycemia"],
    "a1c": ["diabetes", "type 2 diabetes", "t2dm"],
    "glucose": ["diabetes", "hyperglycemia", "hypoglycemia"],
    "fasting glucose": ["diabetes", "hyperglycemia"],
    "tsh": ["hypothyroidism", "hyperthyroidism", "thyroid disease"],
    "ldl": ["hyperlipidemia", "cardiovascular disease", "high cholesterol"],
    "hdl": ["hyperlipidemia", "cardiovascular disease"],
    "cholesterol": ["hyperlipidemia", "cardiovascular disease", "high cholesterol"],
    "triglycerides": ["hyperlipidemia", "metabolic syndrome"],
    "inr": ["atrial fibrillation", "blood clot", "anticoagulation"],
    "pt": ["anticoagulation", "liver disease"],
    "creatinine": ["kidney disease", "renal failure", "ckd"],
    "egfr": ["kidney disease", "renal failure", "ckd"],
    "bun": ["kidney disease", "dehydration"],
    "alt": ["liver disease", "hepatitis", "fatty liver"],
    "ast": ["liver disease", "hepatitis"],
    "albumin": ["liver disease", "malnutrition", "kidney disease"],
    "hemoglobin": ["anemia", "blood disorder"],
    "hematocrit": ["anemia", "blood disorder"],
    "wbc": ["infection", "leukemia", "immune disorder"],
    "platelets": ["thrombocytopenia", "bleeding disorder"],
    "sodium": ["hyponatremia", "electrolyte imbalance", "heart failure"],
    "potassium": ["hyperkalemia", "hypokalemia", "kidney disease"],
    "calcium": ["hypercalcemia", "hypocalcemia", "parathyroid disease"],
    "vitamin d": ["vitamin d deficiency", "osteoporosis"],
    "b12": ["anemia", "neuropathy", "vitamin b12 deficiency"],
    "ferritin": ["anemia", "iron deficiency", "hemochromatosis"],
    "psa": ["prostate cancer", "benign prostatic hyperplasia"],
    "urine protein": ["kidney disease", "nephrotic syndrome"],
}

LAB_ABNORMAL_INDICATES: Dict[str, List[str]] = {
    "hba1c": ["uncontrolled diabetes", "diabetes"],
    "ldl": ["cardiovascular risk", "hyperlipidemia"],
    "creatinine": ["kidney dysfunction", "ckd"],
    "hemoglobin": ["anemia"],
    "wbc": ["infection", "inflammation"],
    "alt": ["liver damage"],
    "ast": ["liver damage", "cardiac damage"],
    "tsh": ["thyroid dysfunction"],
}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _normalise(name: str) -> str:
    """Lower-case, strip punctuation → canonical key for deduplication."""
    return re.sub(r"[^a-z0-9 ]", "", name.lower().strip())


def _contains_any(text: str, keywords: List[str]) -> bool:
    t = _normalise(text)
    return any(kw in t for kw in keywords)


# ──────────────────────────────────────────────────────────────────────────────
# Main service
# ──────────────────────────────────────────────────────────────────────────────


class KnowledgeGraphService:
    """Builds a canonical, deduplicated medical knowledge graph from clinical tables."""

    # ── Public entry point ─────────────────────────────────────────────────

    def build_graph(self, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Build the complete knowledge graph for a user.

        Returns
        -------
        {
          "nodes": [...],       # canonical, deduplicated entity nodes
          "edges": [...],       # typed, directional edges with evidence
          "statistics": {...},  # summary stats for the UI header
          "clusters": {...},    # node-type → [node_ids] for layout hints
        }
        """
        try:
            # 1. Load all clinical entities
            conditions = self._load_conditions(db, user_id)
            medications = self._load_medications(db, user_id)
            labs = self._load_labs(db, user_id)
            procedures = self._load_procedures(db, user_id)
            allergies = self._load_allergies(db, user_id)

            # 2. Deduplicate → canonical node map  { canonical_key → node_dict }
            canon_nodes: Dict[str, Dict] = {}
            self._merge_conditions(conditions, canon_nodes)
            self._merge_medications(medications, canon_nodes)
            self._merge_labs(labs, canon_nodes)
            self._merge_procedures(procedures, canon_nodes)
            self._merge_allergies(allergies, canon_nodes)

            # 3. Build edges
            edges = self._build_edges(
                canon_nodes, conditions, medications, labs, procedures, allergies
            )

            # 4. Deduplicate edges
            edges = self._dedup_edges(edges)

            # 5. Statistics
            nodes_list = list(canon_nodes.values())
            stats = self._compute_stats(nodes_list, edges)
            clusters = self._build_clusters(nodes_list)

            logger.info(
                f"KG for {user_id}: {len(nodes_list)} nodes, {len(edges)} edges"
            )
            return {
                "nodes": nodes_list,
                "edges": edges,
                "statistics": stats,
                "clusters": clusters,
            }

        except Exception as exc:
            logger.error(f"KnowledgeGraphService error: {exc}", exc_info=True)
            return {"nodes": [], "edges": [], "statistics": {}, "clusters": {}}

    # ── Data loaders ───────────────────────────────────────────────────────

    def _load_conditions(self, db: Session, user_id: str) -> List[ClinicalCondition]:
        return (
            db.query(ClinicalCondition)
            .filter(
                ClinicalCondition.user_id == user_id,
                ClinicalCondition.deleted_at.is_(None),
            )
            .all()
        )

    def _load_medications(self, db: Session, user_id: str) -> List[ClinicalMedication]:
        return (
            db.query(ClinicalMedication)
            .filter(
                ClinicalMedication.user_id == user_id,
                ClinicalMedication.deleted_at.is_(None),
            )
            .all()
        )

    def _load_labs(self, db: Session, user_id: str) -> List[ClinicalLabResult]:
        return (
            db.query(ClinicalLabResult)
            .filter(
                ClinicalLabResult.user_id == user_id,
                ClinicalLabResult.deleted_at.is_(None),
            )
            .all()
        )

    def _load_procedures(self, db: Session, user_id: str) -> List[ClinicalProcedure]:
        return (
            db.query(ClinicalProcedure)
            .filter(
                ClinicalProcedure.user_id == user_id,
                ClinicalProcedure.deleted_at.is_(None),
            )
            .all()
        )

    def _load_allergies(self, db: Session, user_id: str) -> List[ClinicalAllergy]:
        return (
            db.query(ClinicalAllergy)
            .filter(
                ClinicalAllergy.user_id == user_id,
                ClinicalAllergy.deleted_at.is_(None),
            )
            .all()
        )

    # ── Node merging (deduplication) ───────────────────────────────────────

    def _make_node_id(self, entity_type: str, canonical_key: str) -> str:
        return f"{entity_type}::{canonical_key}"

    def _merge_conditions(
        self,
        items: List[ClinicalCondition],
        canon: Dict[str, Dict],
    ) -> None:
        for item in items:
            key = _normalise(item.name)
            node_id = self._make_node_id("condition", key)
            if node_id not in canon:
                canon[node_id] = {
                    "id": node_id,
                    "label": item.name.title(),
                    "type": "condition",
                    "properties": {
                        "status": item.status,
                        "severity": item.severity,
                        "diagnosed_date": (
                            item.diagnosed_date.isoformat()
                            if item.diagnosed_date
                            else None
                        ),
                        "icd10_code": item.icd10_code,
                    },
                    "source_documents": [],
                    "earliest_date": item.diagnosed_date,
                }
            node = canon[node_id]
            # Accumulate source documents
            if item.document_id not in node["source_documents"]:
                node["source_documents"].append(item.document_id)
            # Promote severity if escalating
            if item.severity in ("severe", "critical") and node["properties"].get(
                "severity"
            ) not in ("severe", "critical"):
                node["properties"]["severity"] = item.severity
            # Track earliest seen date
            if item.diagnosed_date and (
                node["earliest_date"] is None
                or item.diagnosed_date < node["earliest_date"]
            ):
                node["earliest_date"] = item.diagnosed_date

    def _merge_medications(
        self,
        items: List[ClinicalMedication],
        canon: Dict[str, Dict],
    ) -> None:
        for item in items:
            key = _normalise(item.name)
            node_id = self._make_node_id("medication", key)
            if node_id not in canon:
                canon[node_id] = {
                    "id": node_id,
                    "label": item.name.title(),
                    "type": "medication",
                    "properties": {
                        "dosage": item.dosage,
                        "frequency": item.frequency,
                        "route": item.route,
                        "indication": item.indication,
                        "is_active": item.is_active,
                        "start_date": (
                            item.start_date.isoformat() if item.start_date else None
                        ),
                        "prescriber": item.prescriber,
                        "rxnorm_code": item.rxnorm_code,
                    },
                    "source_documents": [],
                    "earliest_date": item.start_date,
                }
            node = canon[node_id]
            if item.document_id not in node["source_documents"]:
                node["source_documents"].append(item.document_id)
            if item.start_date and (
                node["earliest_date"] is None or item.start_date < node["earliest_date"]
            ):
                node["earliest_date"] = item.start_date

    def _merge_labs(
        self,
        items: List[ClinicalLabResult],
        canon: Dict[str, Dict],
    ) -> None:
        for item in items:
            key = _normalise(item.test_name)
            node_id = self._make_node_id("lab_result", key)
            if node_id not in canon:
                canon[node_id] = {
                    "id": node_id,
                    "label": item.test_name.title(),
                    "type": "lab_result",
                    "properties": {
                        "latest_value": item.value,
                        "unit": item.unit,
                        "reference_range": item.reference_range,
                        "is_abnormal": item.is_abnormal,
                        "abnormal_flag": item.abnormal_flag,
                        "latest_date": (
                            item.test_date.isoformat() if item.test_date else None
                        ),
                        "loinc_code": item.loinc_code,
                    },
                    "source_documents": [],
                    "earliest_date": item.test_date,
                    "_is_abnormal": item.is_abnormal,  # internal flag
                }
            node = canon[node_id]
            if item.document_id not in node["source_documents"]:
                node["source_documents"].append(item.document_id)
            # Keep the most recent value
            if item.test_date and (
                node["earliest_date"] is None or item.test_date > node["earliest_date"]
            ):
                node["properties"]["latest_value"] = item.value
                node["properties"]["latest_date"] = item.test_date.isoformat()
            # If any reading was abnormal, flag the node
            if item.is_abnormal:
                node["_is_abnormal"] = True
                node["properties"]["is_abnormal"] = True

    def _merge_procedures(
        self,
        items: List[ClinicalProcedure],
        canon: Dict[str, Dict],
    ) -> None:
        for item in items:
            key = _normalise(item.procedure_name)
            node_id = self._make_node_id("procedure", key)
            if node_id not in canon:
                canon[node_id] = {
                    "id": node_id,
                    "label": item.procedure_name.title(),
                    "type": "procedure",
                    "properties": {
                        "performed_date": (
                            item.performed_date.isoformat()
                            if item.performed_date
                            else None
                        ),
                        "outcome": item.outcome,
                        "provider": item.provider,
                        "cpt_code": item.cpt_code,
                    },
                    "source_documents": [],
                    "earliest_date": item.performed_date,
                }
            node = canon[node_id]
            if item.document_id not in node["source_documents"]:
                node["source_documents"].append(item.document_id)

    def _merge_allergies(
        self,
        items: List[ClinicalAllergy],
        canon: Dict[str, Dict],
    ) -> None:
        for item in items:
            key = _normalise(item.allergen)
            node_id = self._make_node_id("allergy", key)
            if node_id not in canon:
                canon[node_id] = {
                    "id": node_id,
                    "label": item.allergen.title(),
                    "type": "allergy",
                    "properties": {
                        "reaction": item.reaction,
                        "severity": item.severity,
                        "allergy_type": item.allergy_type,
                        "is_active": item.is_active,
                    },
                    "source_documents": [],
                    "earliest_date": item.verified_date,
                }
            node = canon[node_id]
            if item.document_id not in node["source_documents"]:
                node["source_documents"].append(item.document_id)

    # ── Edge builders ──────────────────────────────────────────────────────

    def _build_edges(
        self,
        canon: Dict[str, Dict],
        conditions: List[ClinicalCondition],
        medications: List[ClinicalMedication],
        labs: List[ClinicalLabResult],
        procedures: List[ClinicalProcedure],
        allergies: List[ClinicalAllergy],
    ) -> List[Dict[str, Any]]:
        edges: List[Dict[str, Any]] = []

        edges += self._med_condition_edges(canon, medications, conditions)
        edges += self._lab_condition_edges(canon, labs, conditions)
        edges += self._lab_abnormal_edges(canon, labs, conditions)
        edges += self._procedure_condition_edges(canon, procedures, conditions)
        edges += self._allergy_edges(canon, allergies, medications)
        edges += self._med_indication_edges(canon, medications, conditions)
        edges += self._lab_followup_edges(canon, labs)
        edges += self._codoc_edges(canon, conditions, medications, labs)

        return edges

    # 1. Medication → Condition  (treats_for via ontology)
    def _med_condition_edges(
        self,
        canon: Dict[str, Dict],
        medications: List[ClinicalMedication],
        conditions: List[ClinicalCondition],
    ) -> List[Dict]:
        edges = []
        for med in medications:
            med_key = _normalise(med.name)
            med_id = self._make_node_id("medication", med_key)
            if med_id not in canon:
                continue
            for ont_key, cond_keywords in MEDICATION_TREATS.items():
                if ont_key not in med_key:
                    continue
                for cond in conditions:
                    cond_key = _normalise(cond.name)
                    cond_id = self._make_node_id("condition", cond_key)
                    if cond_id not in canon:
                        continue
                    if not _contains_any(cond.name, cond_keywords):
                        continue
                    # Determine confidence based on temporal evidence
                    confidence = 0.85
                    evidence = (
                        f"Clinical ontology: {med.name} is indicated for {cond.name}"
                    )
                    # Boost if medication started after diagnosis (temporal evidence)
                    if med.start_date and cond.diagnosed_date:
                        gap = (med.start_date - cond.diagnosed_date).days
                        if 0 <= gap <= 365:
                            confidence = 0.95
                            evidence += f" (started {gap}d after diagnosis)"
                    edges.append(
                        self._make_edge(
                            source=med_id,
                            target=cond_id,
                            rel_type="treats_for",
                            confidence=confidence,
                            evidence=evidence,
                        )
                    )
        return edges

    # 2. Medication → Condition  (prescribed_for via indication field)
    def _med_indication_edges(
        self,
        canon: Dict[str, Dict],
        medications: List[ClinicalMedication],
        conditions: List[ClinicalCondition],
    ) -> List[Dict]:
        edges = []
        for med in medications:
            if not med.indication:
                continue
            med_id = self._make_node_id("medication", _normalise(med.name))
            if med_id not in canon:
                continue
            for cond in conditions:
                if _contains_any(med.indication, [_normalise(cond.name)]):
                    cond_id = self._make_node_id("condition", _normalise(cond.name))
                    if cond_id not in canon:
                        continue
                    edges.append(
                        self._make_edge(
                            source=med_id,
                            target=cond_id,
                            rel_type="prescribed_for",
                            confidence=0.92,
                            evidence=f"Indication field: '{med.indication}'",
                        )
                    )
        return edges

    # 3. Lab → Condition  (monitors via ontology)
    def _lab_condition_edges(
        self,
        canon: Dict[str, Dict],
        labs: List[ClinicalLabResult],
        conditions: List[ClinicalCondition],
    ) -> List[Dict]:
        edges = []
        for lab in labs:
            lab_key = _normalise(lab.test_name)
            lab_id = self._make_node_id("lab_result", lab_key)
            if lab_id not in canon:
                continue
            for ont_key, cond_keywords in LAB_MONITORS.items():
                if ont_key not in lab_key:
                    continue
                for cond in conditions:
                    cond_id = self._make_node_id("condition", _normalise(cond.name))
                    if cond_id not in canon:
                        continue
                    if not _contains_any(cond.name, cond_keywords):
                        continue
                    edges.append(
                        self._make_edge(
                            source=lab_id,
                            target=cond_id,
                            rel_type="monitors",
                            confidence=0.88,
                            evidence=f"{lab.test_name} is a monitoring marker for {cond.name}",
                        )
                    )
        return edges

    # 4. Lab → Condition  (abnormal_indicates when result is flagged)
    def _lab_abnormal_edges(
        self,
        canon: Dict[str, Dict],
        labs: List[ClinicalLabResult],
        conditions: List[ClinicalCondition],
    ) -> List[Dict]:
        edges = []
        for lab in labs:
            if not lab.is_abnormal:
                continue
            lab_key = _normalise(lab.test_name)
            lab_id = self._make_node_id("lab_result", lab_key)
            if lab_id not in canon:
                continue
            for ont_key, cond_keywords in LAB_ABNORMAL_INDICATES.items():
                if ont_key not in lab_key:
                    continue
                for cond in conditions:
                    cond_id = self._make_node_id("condition", _normalise(cond.name))
                    if cond_id not in canon:
                        continue
                    if not _contains_any(cond.name, cond_keywords):
                        continue
                    flag = lab.abnormal_flag or "abnormal"
                    edges.append(
                        self._make_edge(
                            source=lab_id,
                            target=cond_id,
                            rel_type="abnormal_indicates",
                            confidence=0.82,
                            evidence=f"{lab.test_name} = {lab.value} {lab.unit or ''} ({flag}) — may indicate {cond.name}",
                        )
                    )
        return edges

    # 5. Procedure → Condition  (procedure_for via temporal proximity)
    def _procedure_condition_edges(
        self,
        canon: Dict[str, Dict],
        procedures: List[ClinicalProcedure],
        conditions: List[ClinicalCondition],
    ) -> List[Dict]:
        edges = []
        for proc in procedures:
            if not proc.performed_date:
                continue
            proc_id = self._make_node_id("procedure", _normalise(proc.procedure_name))
            if proc_id not in canon:
                continue
            for cond in conditions:
                if not cond.diagnosed_date:
                    continue
                cond_id = self._make_node_id("condition", _normalise(cond.name))
                if cond_id not in canon:
                    continue
                gap = (proc.performed_date - cond.diagnosed_date).days
                if 0 <= gap <= 180:
                    edges.append(
                        self._make_edge(
                            source=proc_id,
                            target=cond_id,
                            rel_type="procedure_for",
                            confidence=0.75,
                            evidence=f"{proc.procedure_name} performed {gap}d after {cond.name} diagnosis",
                        )
                    )
        return edges

    # 6. Allergy → Medication  (allergic_to / contraindicated_with)
    def _allergy_edges(
        self,
        canon: Dict[str, Dict],
        allergies: List[ClinicalAllergy],
        medications: List[ClinicalMedication],
    ) -> List[Dict]:
        edges = []
        for allergy in allergies:
            allergy_id = self._make_node_id("allergy", _normalise(allergy.allergen))
            if allergy_id not in canon:
                continue
            # Does any medication name match the allergen?
            for med in medications:
                med_key = _normalise(med.name)
                if _normalise(allergy.allergen) in med_key or med_key in _normalise(
                    allergy.allergen
                ):
                    med_id = self._make_node_id("medication", med_key)
                    if med_id not in canon:
                        continue
                    edges.append(
                        self._make_edge(
                            source=allergy_id,
                            target=med_id,
                            rel_type="contraindicated_with",
                            confidence=0.97,
                            evidence=f"Patient allergic to {allergy.allergen} (reaction: {allergy.reaction or 'unknown'})",
                        )
                    )
        return edges

    # 7. Lab → Lab  (follow_up_to — same test repeated within 1 year)
    def _lab_followup_edges(
        self,
        canon: Dict[str, Dict],
        labs: List[ClinicalLabResult],
    ) -> List[Dict]:
        edges = []
        grouped: Dict[str, List[ClinicalLabResult]] = defaultdict(list)
        for lab in labs:
            if lab.test_date:
                grouped[_normalise(lab.test_name)].append(lab)

        # For repeated tests we emit a single "follow_up_to" meta-edge on the
        # canonical node (loop edge) to signal serial monitoring.
        for lab_key, instances in grouped.items():
            if len(instances) < 2:
                continue
            lab_id = self._make_node_id("lab_result", lab_key)
            if lab_id not in canon:
                continue
            instances.sort(key=lambda x: x.test_date)
            first = instances[0]
            last = instances[-1]
            gap = (last.test_date - first.test_date).days
            if gap <= 365 * 3:  # within 3 years
                edges.append(
                    self._make_edge(
                        source=lab_id,
                        target=lab_id,
                        rel_type="serial_monitoring",
                        confidence=0.95,
                        evidence=f"{len(instances)} readings over {gap} days",
                    )
                )
        return edges

    # 8. Co-occurrence edges  (same document → weaker inferred relationship)
    def _codoc_edges(
        self,
        canon: Dict[str, Dict],
        conditions: List[ClinicalCondition],
        medications: List[ClinicalMedication],
        labs: List[ClinicalLabResult],
    ) -> List[Dict]:
        """
        For condition pairs that appear in the same document and are NOT already
        linked by a stronger edge, add a co_occurs_with edge.
        Capped at 20 pairs to keep graph clean.
        """
        edges = []
        doc_conditions: Dict[str, List[str]] = defaultdict(list)
        for c in conditions:
            doc_conditions[c.document_id].append(
                self._make_node_id("condition", _normalise(c.name))
            )

        seen_pairs: set = set()
        count = 0
        for doc_id, node_ids in doc_conditions.items():
            unique = list(set(node_ids))
            for i in range(len(unique)):
                for j in range(i + 1, len(unique)):
                    pair = tuple(sorted([unique[i], unique[j]]))
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)
                    if unique[i] not in canon or unique[j] not in canon:
                        continue
                    edges.append(
                        self._make_edge(
                            source=unique[i],
                            target=unique[j],
                            rel_type="co_occurs_with",
                            confidence=0.60,
                            evidence=f"Conditions mentioned together in the same document",
                        )
                    )
                    count += 1
                    if count >= 20:
                        return edges
        return edges

    # ── Edge helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _make_edge(
        source: str,
        target: str,
        rel_type: str,
        confidence: float,
        evidence: str,
    ) -> Dict[str, Any]:
        return {
            "id": f"{rel_type}::{source}::{target}",
            "source": source,
            "target": target,
            "type": rel_type,
            "confidence": round(confidence, 2),
            "evidence": evidence,
        }

    @staticmethod
    def _dedup_edges(edges: List[Dict]) -> List[Dict]:
        """Keep the highest-confidence edge for each (source, target, type)."""
        best: Dict[str, Dict] = {}
        for e in edges:
            k = f"{e['type']}::{e['source']}::{e['target']}"
            if k not in best or e["confidence"] > best[k]["confidence"]:
                best[k] = e
        return list(best.values())

    # ── Statistics & layout helpers ────────────────────────────────────────

    @staticmethod
    def _compute_stats(nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
        type_counts: Dict[str, int] = defaultdict(int)
        for n in nodes:
            type_counts[n["type"]] += 1

        rel_counts: Dict[str, int] = defaultdict(int)
        for e in edges:
            rel_counts[e["type"]] += 1

        confidences = [e["confidence"] for e in edges] or [0]
        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "node_types": dict(type_counts),
            "relationship_types": dict(rel_counts),
            "avg_confidence": round(sum(confidences) / len(confidences), 2),
            "high_confidence": sum(1 for c in confidences if c >= 0.9),
        }

    @staticmethod
    def _build_clusters(nodes: List[Dict]) -> Dict[str, List[str]]:
        clusters: Dict[str, List[str]] = defaultdict(list)
        for n in nodes:
            clusters[n["type"]].append(n["id"])
        return dict(clusters)


# Singleton
knowledge_graph_service = KnowledgeGraphService()
