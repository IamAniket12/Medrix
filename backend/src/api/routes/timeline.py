"""Unified Timeline API — enriched events + stats + intelligence in one call."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from src.core.dependencies import get_db
from src.services.timeline_service import timeline_service

router = APIRouter()


@router.get("/{user_id}")
async def get_timeline(
    user_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    importance: Optional[str] = Query(None, description="high | medium | low"),
    start_date: Optional[str] = Query(
        None, description="ISO date string, e.g. 2024-01-01"
    ),
    end_date: Optional[str] = Query(
        None, description="ISO date string, e.g. 2024-12-31"
    ),
    limit: int = Query(200, le=500, description="Max events to return"),
    db: Session = Depends(get_db),
):
    """
    Unified timeline endpoint.

    Returns a single response containing:
    - `events`  — enriched timeline events with inline related clinical detail
                  (no N+1 — all related entities loaded in bulk)
    - `stats`   — aggregate counts by type, importance, date range
    - `insights` — health score, predictions, adherence alerts, disease progression

    This supersedes the three separate calls previously needed:
      GET /clinical/timeline/{user_id}
      GET /clinical/timeline/{user_id}/stats
      GET /clinical/timeline/{user_id}/insights
    """
    return await timeline_service.build_timeline(
        db=db,
        user_id=user_id,
        event_type=event_type,
        importance=importance,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
