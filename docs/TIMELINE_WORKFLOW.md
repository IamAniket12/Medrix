# Timeline — How It Works

The timeline assembles every clinical event in a patient's history, enriches each one with full inline detail from the related clinical entity, adds aggregate statistics, and layers on AI-driven intelligence (health score, predictions, alerts, disease progression). All of this is returned in a single API response.

---

## Step 1 — Frontend sends one request

The page at `frontend/app/timeline/page.tsx` fires one `fetch` call on mount (and again whenever a filter changes):

```
GET /api/v1/timeline/{user_id}?event_type=&importance=&start_date=&end_date=&limit=200
```

All filters are optional. The default limit is 200 events.

This replaced the old design that required **three separate fetches**:
- `GET /clinical/timeline/{user_id}` — events
- `GET /clinical/timeline/{user_id}/stats` — statistics
- `GET /clinical/timeline/{user_id}/insights` — intelligence

---

## Step 2 — Route handler receives the request

`backend/src/api/routes/timeline.py`

The `GET /{user_id}` handler accepts five optional query parameters and passes them straight to the service singleton:

```python
return await timeline_service.build_timeline(
    db=db, user_id=user_id,
    event_type=event_type, importance=importance,
    start_date=start_date, end_date=end_date,
    limit=limit,
)
```

The route registers at `/api/v1/timeline/{user_id}` via `backend/src/api/v1/__init__.py`.

---

## Step 3 — Service builds the filtered event query

`backend/src/services/timeline_service.py` → `build_timeline()`

A SQLAlchemy query against the `timeline_events` table is constructed dynamically:

1. Always filters `user_id = {user_id}` and `deleted_at IS NULL`
2. Conditionally adds:
   - `event_type = ?` if provided
   - `importance = ?` if provided
   - `event_date >= ?` if `start_date` provided (parsed as ISO datetime)
   - `event_date <= ?` if `end_date` provided
3. Counts the **filtered** rows before applying the limit (used in `stats.filtered_count`)
4. Orders by `event_date DESC`, applies `LIMIT`

---

## Step 4 — All related entities are bulk-loaded (no N+1)

Rather than fetching each event's related clinical entity one by one, the service collects all FK IDs from the returned events and issues **five IN queries**:

```python
condition_ids  = [e.related_condition_id  for e in events if e.related_condition_id]
medication_ids = [e.related_medication_id for e in events if e.related_medication_id]
procedure_ids  = [e.related_procedure_id  for e in events if e.related_procedure_id]
lab_ids        = [e.related_lab_result_id for e in events if e.related_lab_result_id]
doc_ids        = list({e.document_id for e in events if e.document_id})
```

Each group is loaded in a single `WHERE id IN (...)` query and stored in a dict keyed by ID:

```python
conditions_map  = {c.id: c for c in rows}
medications_map = {m.id: m for m in rows}
# ... etc
```

For 200 events this is always exactly 5 queries, regardless of how many unique related entities exist. The old approach would have been up to 800 individual queries.

---

## Step 5 — Each event is enriched with inline clinical detail

The service iterates the events and builds an `enriched_event` dict for each one. If the event has a related entity FK, the full entity object is inlined as `related_detail`:

| FK present on event | Key added to `related_detail` | Fields included |
|---|---|---|
| `related_condition_id` | `condition` | name, status, severity, icd10_code, body_site, diagnosed_date, notes |
| `related_medication_id` | `medication` | name, dosage, frequency, route, start_date, end_date, prescriber, indication, is_active, rxnorm_code |
| `related_procedure_id` | `procedure` | procedure_name, performed_date, provider, facility, body_site, indication, outcome, cpt_code |
| `related_lab_result_id` | `lab_result` | test_name, value, unit, reference_range, is_abnormal, abnormal_flag, test_date, ordering_provider, lab_facility, loinc_code |

If the event has a `document_id`, a summary `{ id, filename, document_type }` is attached under `document`.

If an event has no related entity, `related_detail` is an empty dict `{}`.

---

## Step 6 — Aggregate statistics are computed

A second pass over the database (not the filtered result set) computes stats across **all** events for the user:

| Stat | How computed |
|---|---|
| `total_events` | `COUNT(*)` on all non-deleted events for user |
| `filtered_count` | Count from Step 3 before the LIMIT |
| `recent_events_30d` | COUNT where `event_date >= NOW() - 30 days` |
| `by_type` | `GROUP BY event_type` → `{ "diagnosis": 12, "lab_result": 34, … }` |
| `by_importance` | `GROUP BY importance` → `{ "high": 8, "medium": 22, "low": 41 }` |
| `date_range` | `MIN(event_date)` and `MAX(event_date)` |

---

## Step 7 — Intelligence layer runs

The service instantiates `TimelineIntelligenceService(db)` and calls four methods:

### 7a — Health score
`intel.generate_health_score(user_id)`

Scores the patient across multiple dimensions (medication adherence, lab trends, condition severity, care gaps) and returns:
```json
{
  "total_score": 72,
  "grade": "B",
  "breakdown": { "medication_adherence": 80, "lab_trends": 65, ... },
  "insights": ["HbA1c trending up — consider follow-up", ...]
}
```

### 7b — Upcoming predictions
`intel.predict_upcoming_events(user_id)`

Analyses the event history to predict events that are due or overdue, e.g. annual labs, medication refills, follow-up appointments. Returns a list of `{ type, priority, message, recommended_action }` objects.

### 7c — Medication adherence alerts
`intel.detect_medication_adherence_gaps(user_id)`

Looks for active medications where there is no recent refill or continuation event, flagging potential adherence gaps. Returns a list of `{ type, severity, message, recommendation }` alerts.

### 7d — Disease progression trends
`intel.detect_disease_progression(user_id, condition_name)` is called for three key conditions: `diabetes`, `hypertension`, `hyperlipidemia`.

For each, the service finds the relevant lab test series (e.g. HbA1c for diabetes), compares first and last values, and classifies the trend as `improving`, `stable`, or `worsening`.

---

## Step 8 — Single unified response is returned

```json
{
  "events": [
    {
      "id": "evt-uuid",
      "event_date": "2024-06-15",
      "event_type": "lab_result",
      "event_title": "HbA1c Result",
      "event_description": "Quarterly diabetes monitoring",
      "importance": "high",
      "provider": "Dr. Smith",
      "facility": "City Medical Center",
      "document": { "id": "doc-uuid", "filename": "labs_june.pdf", "document_type": "lab_report" },
      "related_detail": {
        "lab_result": {
          "test_name": "HbA1c",
          "value": "8.2",
          "unit": "%",
          "reference_range": "< 5.7",
          "is_abnormal": true,
          "abnormal_flag": "H"
        }
      }
    }
  ],
  "stats": {
    "total_events": 87,
    "filtered_count": 87,
    "recent_events_30d": 4,
    "by_type": { "lab_result": 34, "diagnosis": 12, "medication_started": 8 },
    "by_importance": { "high": 8, "medium": 22, "low": 57 },
    "date_range": { "earliest": "2019-03-01", "latest": "2025-01-20" }
  },
  "insights": {
    "health_score": { "total_score": 72, "grade": "B", "breakdown": {}, "insights": [] },
    "predictions": [...],
    "alerts": [...],
    "disease_progression": [...]
  }
}
```

---

## Step 9 — Frontend renders the timeline

`frontend/app/timeline/page.tsx` processes the response client-side only:

1. **Grouping** — Events are grouped in memory first by year, then by month. No additional requests are made.
2. **Year-rail** — A sticky left sidebar lists all years found in the grouped data. Clicking a year calls `scrollIntoView` on the corresponding DOM section.
3. **Event cards** — Each event renders as a glass card on a vertical line. The importance level (`high` / `medium` / `low`) determines the dot colour and glow; the event type determines the icon inside the dot.
4. **Expandable detail** — Clicking a card with `related_detail` toggles an `EventDetail` section that renders the inlined condition, medication, lab result, or procedure fields with type-appropriate chips and colour coding.
5. **Stats strip** — Four `StatCard` components show totals from the `stats` block; a `HealthRing` SVG gauge renders the health score.
6. **Insights panel** (shown via toggle) — Displays health score insights, upcoming predictions, adherence alerts, and disease progression trends. The toggle button badge shows the total alert count.
7. **Filter bar** (shown via toggle) — Controls `event_type`, `importance`, `start_date`, `end_date` filters which re-trigger `fetchData`. A client-side text search filters the already-loaded events without any additional API call.

---

## Data flow summary

```
Browser
  └─ GET /api/v1/timeline/{user_id}?[filters]
       └─ timeline.py (route)
            └─ timeline_service.build_timeline()
                 ├─ 1. Build filtered event query (with optional type/importance/date filters)
                 ├─ 2. Bulk-load related entities via 5 IN queries (no N+1)
                 ├─ 3. Enrich each event with inline related_detail + document
                 ├─ 4. Compute aggregate stats (total, 30d, by_type, by_importance, date_range)
                 ├─ 5. Run intelligence layer
                 │       ├─ generate_health_score()
                 │       ├─ predict_upcoming_events()
                 │       ├─ detect_medication_adherence_gaps()
                 │       └─ detect_disease_progression() × 3 conditions
                 └─ Return { events, stats, insights }
  └─ Frontend groups events by year → month
       ├─ Year-rail for navigation
       ├─ Event cards with expandable detail
       ├─ Stats strip + HealthRing gauge
       └─ Insights panel (toggle) + Filter bar (toggle)
```
