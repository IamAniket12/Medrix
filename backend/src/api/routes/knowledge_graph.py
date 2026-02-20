"""Knowledge Graph API endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict

from src.core.database import get_db
from src.services.knowledge_graph_service import knowledge_graph_service

router = APIRouter(tags=["knowledge-graph"])


@router.get("/{user_id}")
async def get_knowledge_graph(
    user_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Return a fully-built, deduplicated clinical knowledge graph for a user.

    Response shape
    --------------
    {
      "nodes": [
        {
          "id":               "medication::metformin",
          "label":            "Metformin",
          "type":             "medication" | "condition" | "lab_result" | "procedure" | "allergy",
          "properties":       { ...entity-specific fields... },
          "source_documents": ["doc-uuid-1", ...],
          "earliest_date":    "2024-01-15" | null
        },
        ...
      ],
      "edges": [
        {
          "id":         "treats_for::medication::metformin::condition::diabetes",
          "source":     "medication::metformin",
          "target":     "condition::diabetes",
          "type":       "treats_for" | "prescribed_for" | "monitors" |
                        "abnormal_indicates" | "procedure_for" |
                        "contraindicated_with" | "serial_monitoring" | "co_occurs_with",
          "confidence": 0.95,
          "evidence":   "Clinical ontology: Metformin is indicated for Diabetes ..."
        },
        ...
      ],
      "statistics": {
        "total_nodes": 12,
        "total_edges": 18,
        "node_types":         { "medication": 4, "condition": 3, ... },
        "relationship_types": { "treats_for": 5, "monitors": 6, ... },
        "avg_confidence": 0.87,
        "high_confidence": 10
      },
      "clusters": {
        "medication": ["medication::metformin", ...],
        "condition":  ["condition::diabetes", ...],
        ...
      }
    }
    """
    try:
        result = knowledge_graph_service.build_graph(db=db, user_id=user_id)

        if not result["nodes"]:
            return {
                "nodes": [],
                "edges": [],
                "statistics": {
                    "total_nodes": 0,
                    "total_edges": 0,
                    "node_types": {},
                    "relationship_types": {},
                    "avg_confidence": 0,
                    "high_confidence": 0,
                },
                "clusters": {},
                "message": "No clinical data found. Upload and process medical documents to build your knowledge graph.",
            }

        # Serialise dates on nodes before returning
        for node in result["nodes"]:
            if node.get("earliest_date") and not isinstance(node["earliest_date"], str):
                node["earliest_date"] = node["earliest_date"].isoformat()
            # Strip internal flags
            node.pop("_is_abnormal", None)

        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build knowledge graph: {str(exc)}",
        )
