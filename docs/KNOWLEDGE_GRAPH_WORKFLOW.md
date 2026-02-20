# Knowledge Graph — How It Works

The knowledge graph builds a deduplicated, relationship-rich clinical graph from a patient's extracted medical records. Here is the end-to-end flow from browser request to rendered graph.

---

## Step 1 — Frontend sends a single request

The page at `frontend/app/knowledge-graph/page.tsx` fires one `fetch` call on mount:

```
GET /api/v1/knowledge-graph/{user_id}
```

No filters, no pagination — the full graph for the patient is always requested.

---

## Step 2 — Route handler receives the request

`backend/src/api/routes/knowledge_graph.py`

The `GET /{user_id}` handler opens a database session via dependency injection and immediately delegates to the service singleton:

```python
return await knowledge_graph_service.build_graph(db=db, user_id=user_id)
```

All logic lives in the service; the route is a thin pass-through.

---

## Step 3 — Service loads all clinical entities in parallel

`backend/src/services/knowledge_graph_service.py` → `build_graph()`

Five separate queries run, one per entity type:

| Query | Table | What it loads |
|---|---|---|
| `_load_conditions` | `clinical_conditions` | All active diagnoses |
| `_load_medications` | `clinical_medications` | All prescriptions |
| `_load_labs` | `clinical_lab_results` | All lab test results |
| `_load_procedures` | `clinical_procedures` | All procedures & surgeries |
| `_load_allergies` | `clinical_allergies` | All known allergies |

Each query filters `deleted_at IS NULL` so soft-deleted records are excluded automatically.

---

## Step 4 — Entities are deduplicated into canonical nodes

`_merge_conditions()`, `_merge_medications()`, `_merge_labs()`, etc.

The core insight: the same condition (e.g. "Hypertension") may appear in many uploaded documents. Rather than creating one node per occurrence, the service assigns each entity a **canonical key** by normalising its name:

```python
key = _normalise(item.name)   # lower-case, strip punctuation, collapse whitespace
node_id = f"{entity_type}::{key}"   # e.g. "condition::hypertension"
```

If a node for that key already exists:
- The source document is appended to `source_documents[]`
- Severity is **promoted** if the new record is more severe than the existing one
- `earliest_date` is updated to the oldest seen date

This means "Hypertension" across 5 documents becomes **one node** with 5 source document IDs attached.

---

## Step 5 — Typed, directional edges are built

`_build_edges()`

Edges are inferred using three methods, applied in priority order:

### 5a — Clinical ontology lookup (highest confidence, ~0.9–0.95)

Two static dictionary maps encode domain knowledge:

- `MEDICATION_TREATS` — maps ~30 common medications to the conditions they treat  
  `"metformin" → ["diabetes", "type 2 diabetes", "t2dm", "hyperglycemia"]`
- `LAB_MONITORS` — maps ~30 lab test names to the conditions they monitor  
  `"hba1c" → ["diabetes", "t2dm"]`

When a medication node exists and its name is in `MEDICATION_TREATS`, the service checks whether any condition node matches any of the listed conditions. If yes → `treats_for` or `prescribed_for` edge, confidence 0.90–0.95.

### 5b — Temporal co-occurrence (medium confidence, ~0.7)

If a medication was started within 30 days of a diagnosis, that temporal proximity is used as evidence for a `treats_for` edge with the evidence string:

```
"Temporal: Metformin started 12 days after Diabetes diagnosis"
```

### 5c — Document co-occurrence (lowest confidence, 0.5)

Entities that share the same `document_id` but have no ontology match get a `co_occurs_with` edge, signalling they appeared in the same clinical document.

### Edge types used

| Type | Meaning |
|---|---|
| `treats_for` | Medication treats a condition |
| `prescribed_for` | Medication prescribed specifically for a condition |
| `monitors` | Lab result tracks a condition |
| `abnormal_indicates` | Abnormal lab result flags a potential condition |
| `procedure_for` | Procedure performed to treat a condition |
| `contraindicated_with` | Medication has a known contraindication with a condition or allergy |
| `serial_monitoring` | Multiple labs of the same type ordered over time |
| `co_occurs_with` | Entities appear in the same document (weak signal) |

Each edge carries `confidence` (0–1) and a human-readable `evidence` string explaining why it was created.

---

## Step 6 — Edges are deduplicated

`_dedup_edges()`

Multiple passes through the logic can generate the same edge at different confidence levels. The deduplication step keeps only the **highest-confidence** version of each `(source, target, type)` triple.

---

## Step 7 — Statistics and clusters are computed

`_compute_stats()` — counts nodes and edges by type, calculates average confidence, and counts high-confidence edges (≥ 0.8).

`_build_clusters()` — groups node IDs by entity type (`medication`, `condition`, `lab_result`, `procedure`, `allergy`) so the frontend can apply clustered layouts.

---

## Step 8 — Response is returned to the frontend

```json
{
  "nodes": [
    {
      "id": "condition::hypertension",
      "label": "Hypertension",
      "type": "condition",
      "properties": { "status": "active", "severity": "moderate", "icd10_code": "I10" },
      "source_documents": ["doc-uuid-1", "doc-uuid-2"],
      "earliest_date": "2022-03-15"
    }
  ],
  "edges": [
    {
      "id": "treats_for::medication::lisinopril::condition::hypertension",
      "source": "medication::lisinopril",
      "target": "condition::hypertension",
      "type": "treats_for",
      "confidence": 0.95,
      "evidence": "Clinical ontology: Lisinopril is indicated for Hypertension"
    }
  ],
  "statistics": { "total_nodes": 12, "total_edges": 18, "avg_confidence": 0.87 },
  "clusters": { "medication": [...], "condition": [...] }
}
```

---

## Step 9 — Frontend renders the graph

`frontend/app/knowledge-graph/page.tsx` processes the response:

1. **Layout** — Nodes are positioned in concentric rings by cluster. Conditions occupy the inner ring, medications and labs radiate outward.
2. **Custom nodes** — Each node is rendered as an `EntityNode` component with a type-coloured icon, label, and document source count.
3. **Edges** — ReactFlow `<Edge>` components are coloured and styled by relationship type. Confidence is shown on hover.
4. **NodeDetailPanel** — Clicking a node opens a side panel with all properties, source documents, and connected edges listed.
5. **Stats bar** — The statistics block is shown in the header: total nodes, edges, avg confidence.

---

## Data flow summary

```
Browser
  └─ GET /api/v1/knowledge-graph/{user_id}
       └─ knowledge_graph.py (route)
            └─ knowledge_graph_service.build_graph()
                 ├─ Load conditions, medications, labs, procedures, allergies (5 queries)
                 ├─ Deduplicate into canonical nodes (name normalisation + merge)
                 ├─ Build typed edges (ontology → temporal → co-occurrence)
                 ├─ Dedup edges (keep highest confidence per triple)
                 ├─ Compute statistics & clusters
                 └─ Return { nodes, edges, statistics, clusters }
  └─ ReactFlow renders graph with EntityNode + typed edges + NodeDetailPanel
```
