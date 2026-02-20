"""
Unified Timeline Service
Returns enriched events + stats + insights in a single query pass.
Eliminates the N+1 problem of fetching related clinical entities one-by-one.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from ..models import (
    TimelineEvent,
    ClinicalCondition,
    ClinicalMedication,
    ClinicalLabResult,
    ClinicalProcedure,
    Document,
)
from .timeline_intelligence import TimelineIntelligenceService


class TimelineService:
    """
    Builds a fully enriched, unified timeline payload.

    Design principles (Google / Meta KG style):
    - Single DB round-trip using bulk IN queries (no N+1)
    - Inline related clinical entity detail on each event
    - Unified response: events + stats + intelligence insights
    - Frontend gets everything it needs in one fetch
    """

    async def build_timeline(
        self,
        db: Session,
        user_id: str,
        event_type: Optional[str] = None,
        importance: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 200,
    ) -> Dict[str, Any]:
        # ── 1. Build filtered event query ─────────────────────────────────
        query = db.query(TimelineEvent).filter(
            TimelineEvent.user_id == user_id,
            TimelineEvent.deleted_at.is_(None),
        )

        if event_type:
            query = query.filter(TimelineEvent.event_type == event_type)

        if importance:
            query = query.filter(TimelineEvent.importance == importance)

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                query = query.filter(TimelineEvent.event_date >= start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                query = query.filter(TimelineEvent.event_date <= end_dt)
            except ValueError:
                pass

        filtered_count = query.count()

        events: List[TimelineEvent] = (
            query.order_by(TimelineEvent.event_date.desc()).limit(limit).all()
        )

        # ── 2. Bulk-load all related entities (no N+1) ────────────────────
        condition_ids = [
            e.related_condition_id for e in events if e.related_condition_id
        ]
        medication_ids = [
            e.related_medication_id for e in events if e.related_medication_id
        ]
        procedure_ids = [
            e.related_procedure_id for e in events if e.related_procedure_id
        ]
        lab_ids = [e.related_lab_result_id for e in events if e.related_lab_result_id]
        doc_ids = list({e.document_id for e in events if e.document_id})

        conditions_map: Dict[str, ClinicalCondition] = {}
        if condition_ids:
            rows = (
                db.query(ClinicalCondition)
                .filter(ClinicalCondition.id.in_(condition_ids))
                .all()
            )
            conditions_map = {c.id: c for c in rows}

        medications_map: Dict[str, ClinicalMedication] = {}
        if medication_ids:
            rows = (
                db.query(ClinicalMedication)
                .filter(ClinicalMedication.id.in_(medication_ids))
                .all()
            )
            medications_map = {m.id: m for m in rows}

        procedures_map: Dict[str, ClinicalProcedure] = {}
        if procedure_ids:
            rows = (
                db.query(ClinicalProcedure)
                .filter(ClinicalProcedure.id.in_(procedure_ids))
                .all()
            )
            procedures_map = {p.id: p for p in rows}

        labs_map: Dict[str, ClinicalLabResult] = {}
        if lab_ids:
            rows = (
                db.query(ClinicalLabResult)
                .filter(ClinicalLabResult.id.in_(lab_ids))
                .all()
            )
            labs_map = {l.id: l for l in rows}

        docs_map: Dict[str, Document] = {}
        if doc_ids:
            rows = db.query(Document).filter(Document.id.in_(doc_ids)).all()
            docs_map = {d.id: d for d in rows}

        # ── 3. Build enriched event list ──────────────────────────────────
        enriched_events = []
        for event in events:
            doc = docs_map.get(event.document_id)

            related_detail: Dict[str, Any] = {}

            if (
                event.related_condition_id
                and event.related_condition_id in conditions_map
            ):
                c = conditions_map[event.related_condition_id]
                related_detail["condition"] = {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "severity": c.severity,
                    "body_site": c.body_site,
                    "diagnosed_date": (
                        c.diagnosed_date.isoformat() if c.diagnosed_date else None
                    ),
                    "icd10_code": c.icd10_code,
                    "notes": c.notes,
                }

            if (
                event.related_medication_id
                and event.related_medication_id in medications_map
            ):
                m = medications_map[event.related_medication_id]
                related_detail["medication"] = {
                    "id": m.id,
                    "name": m.name,
                    "dosage": m.dosage,
                    "frequency": m.frequency,
                    "route": m.route,
                    "start_date": m.start_date.isoformat() if m.start_date else None,
                    "end_date": m.end_date.isoformat() if m.end_date else None,
                    "prescriber": m.prescriber,
                    "indication": m.indication,
                    "is_active": m.is_active,
                    "rxnorm_code": m.rxnorm_code,
                }

            if (
                event.related_procedure_id
                and event.related_procedure_id in procedures_map
            ):
                p = procedures_map[event.related_procedure_id]
                related_detail["procedure"] = {
                    "id": p.id,
                    "procedure_name": p.procedure_name,
                    "performed_date": (
                        p.performed_date.isoformat() if p.performed_date else None
                    ),
                    "provider": p.provider,
                    "facility": p.facility,
                    "body_site": p.body_site,
                    "indication": p.indication,
                    "outcome": p.outcome,
                    "cpt_code": p.cpt_code,
                }

            if event.related_lab_result_id and event.related_lab_result_id in labs_map:
                l = labs_map[event.related_lab_result_id]
                related_detail["lab_result"] = {
                    "id": l.id,
                    "test_name": l.test_name,
                    "value": l.value,
                    "unit": l.unit,
                    "reference_range": l.reference_range,
                    "is_abnormal": l.is_abnormal,
                    "abnormal_flag": l.abnormal_flag,
                    "test_date": l.test_date.isoformat() if l.test_date else None,
                    "ordering_provider": l.ordering_provider,
                    "lab_facility": l.lab_facility,
                    "loinc_code": l.loinc_code,
                }

            enriched_events.append(
                {
                    "id": event.id,
                    "event_date": (
                        event.event_date.isoformat() if event.event_date else None
                    ),
                    "event_type": event.event_type,
                    "event_title": event.event_title,
                    "event_description": event.event_description,
                    "importance": event.importance,
                    "provider": event.provider,
                    "facility": event.facility,
                    "document": (
                        {
                            "id": doc.id,
                            "filename": doc.original_name,
                            "document_type": doc.document_type,
                        }
                        if doc
                        else None
                    ),
                    "related_detail": related_detail,
                }
            )

        # ── 4. Compute aggregate stats ─────────────────────────────────────
        all_q = db.query(TimelineEvent).filter(
            TimelineEvent.user_id == user_id,
            TimelineEvent.deleted_at.is_(None),
        )

        total_events = all_q.count()

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_30d = all_q.filter(TimelineEvent.event_date >= thirty_days_ago).count()

        by_type_raw = (
            db.query(TimelineEvent.event_type, func.count(TimelineEvent.id))
            .filter(
                TimelineEvent.user_id == user_id, TimelineEvent.deleted_at.is_(None)
            )
            .group_by(TimelineEvent.event_type)
            .all()
        )

        by_importance_raw = (
            db.query(TimelineEvent.importance, func.count(TimelineEvent.id))
            .filter(
                TimelineEvent.user_id == user_id, TimelineEvent.deleted_at.is_(None)
            )
            .group_by(TimelineEvent.importance)
            .all()
        )

        date_range_q = (
            db.query(
                func.min(TimelineEvent.event_date),
                func.max(TimelineEvent.event_date),
            )
            .filter(
                TimelineEvent.user_id == user_id, TimelineEvent.deleted_at.is_(None)
            )
            .first()
        )

        # ── 5. Intelligence layer ──────────────────────────────────────────
        intel = TimelineIntelligenceService(db)

        health_score = intel.generate_health_score(user_id)
        predictions = intel.predict_upcoming_events(user_id)
        adherence_alerts = intel.detect_medication_adherence_gaps(user_id)

        progressions = []
        for cond_name in ["diabetes", "hypertension", "hyperlipidemia"]:
            prog = intel.detect_disease_progression(user_id, cond_name)
            if prog:
                progressions.append(prog)

        return {
            "events": enriched_events,
            "stats": {
                "total_events": total_events,
                "filtered_count": filtered_count,
                "recent_events_30d": recent_30d,
                "by_type": {t: c for t, c in by_type_raw},
                "by_importance": {imp: c for imp, c in by_importance_raw},
                "date_range": {
                    "earliest": (
                        date_range_q[0].isoformat()
                        if date_range_q and date_range_q[0]
                        else None
                    ),
                    "latest": (
                        date_range_q[1].isoformat()
                        if date_range_q and date_range_q[1]
                        else None
                    ),
                },
            },
            "insights": {
                "health_score": health_score,
                "predictions": predictions,
                "alerts": adherence_alerts,
                "disease_progression": progressions,
            },
        }


# Singleton instance
timeline_service = TimelineService()
