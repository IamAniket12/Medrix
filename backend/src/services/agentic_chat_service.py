"""Agentic RAG chat pipeline using LangChain.

Stages:
1) Intent classification (lightweight heuristics)
2) Retrieval fan-out (documents, timeline events, clinical entities)
3) Rerank/merge with simple scoring
4) Prompt construction with structured JSON ask
5) Model call via MedGemma
6) Output normalization/validation
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ValidationError

from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from src.services.medgemma_service import MedGemmaService
from src.services.embeddings_service import embeddings_service


class StructuredAnswer(BaseModel):
    answer: str
    key_details: List[str]
    citations: List[str]
    note: str


class AgenticChatService:
    def __init__(self, medgemma: MedGemmaService):
        self.medgemma = medgemma
        self.chain = (
            RunnablePassthrough()
            .assign(intent=RunnableLambda(self._classify_intent))
            .assign(retrieval=RunnableLambda(self._retrieve_context))
            .assign(prompt=RunnableLambda(self._build_prompt))
            .assign(response=RunnableLambda(self._call_model))
            .assign(normalized=RunnableLambda(self._normalize_output))
        )

    async def run(
        self,
        db: Any,
        user_id: str,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        base_state = {
            "db": db,
            "user_id": user_id,
            "question": question.strip(),
            "conversation_history": conversation_history or [],
        }
        result = await self.chain.ainvoke(base_state)
        return result.get("normalized", {})

    # --- LangChain node functions ---

    def _classify_intent(self, state: Dict[str, Any]) -> str:
        q = state.get("question", "").lower()
        if any(k in q for k in ["medication", "medicine", "drug", "taking"]):
            return "medication"
        if any(k in q for k in ["lab", "blood", "result", "hba1c", "glucose"]):
            return "labs"
        if any(k in q for k in ["condition", "diagnosis", "disease"]):
            return "condition"
        if any(k in q for k in ["procedure", "surgery", "operation"]):
            return "procedure"
        return "general"

    def _retrieve_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        db = state["db"]
        user_id = state["user_id"]
        question = state["question"]

        # Structured context (active meds/conditions/events) for precise answers like start dates
        patient_context = embeddings_service.get_patient_context(
            db=db, user_id=user_id, current_document_date=None, limit=20
        )

        # Documents
        doc_hits = embeddings_service.search_similar_documents(
            db=db, user_id=user_id, query=question, limit=12
        )

        # Timeline events (often contain start dates)
        event_hits = embeddings_service.search_similar_timeline_events(
            db=db, user_id=user_id, query=question, limit=8
        )

        # Clinical entities (meds/conditions/labs) for direct lookups
        entity_hits = embeddings_service.search_similar_clinical_entities(
            db=db, user_id=user_id, query=question, limit=8
        )

        unified: List[Dict[str, Any]] = []
        primary_document_id: Optional[str] = None

        # Active medications with start dates from structured context
        for med in patient_context.get("active_medications", []):
            unified.append(
                {
                    "type": "active_medication",
                    "source_id": med.get("name"),
                    "content": f"Medication: {med.get('name')} | Dosage: {med.get('dosage')} | Frequency: {med.get('frequency')} | Started: {med.get('start_date')}",
                    "metadata": {
                        "start_date": med.get("start_date"),
                        "prescriber": med.get("prescriber"),
                    },
                    "similarity_score": 1.0,  # structured fact: keep high priority
                    "chunk_index": 0,
                }
            )

        for idx_doc, hit in enumerate(doc_hits):
            if idx_doc == 0:
                primary_document_id = hit.get("document_id")
            unified.append(
                {
                    "type": "document",
                    "source_id": hit["document_id"],
                    "content": hit["chunk_text"],
                    "metadata": {
                        "document_type": hit.get("document_type"),
                        "document_date": hit.get("document_date"),
                        "filename": hit.get("filename"),
                        "original_name": hit.get("original_name"),
                    },
                    "similarity_score": hit.get("similarity_score", 0.0),
                    "chunk_index": hit.get("chunk_index", 0),
                }
            )

        for hit in event_hits:
            unified.append(
                {
                    "type": "timeline_event",
                    "source_id": hit["event_id"],
                    "content": hit.get("event_summary", ""),
                    "metadata": {
                        "event_type": hit.get("event_type"),
                        "event_date": hit.get("event_date"),
                        "event_title": hit.get("event_title"),
                        "importance": hit.get("importance"),
                    },
                    "similarity_score": hit.get("similarity_score", 0.0),
                    "chunk_index": 0,
                }
            )

        for hit in entity_hits:
            unified.append(
                {
                    "type": "entity",
                    "source_id": hit["entity_id"],
                    "content": hit.get("entity_summary", ""),
                    "metadata": {
                        "entity_type": hit.get("entity_type"),
                        "entity_name": hit.get("entity_name"),
                        "first_seen": hit.get("first_seen"),
                        "last_seen": hit.get("last_seen"),
                    },
                    "similarity_score": hit.get("similarity_score", 0.0),
                    "chunk_index": 0,
                }
            )

        # Similarity-only sort
        unified = sorted(
            unified,
            key=lambda item: float(item.get("similarity_score", 0.0)),
            reverse=True,
        )

        # Thresholding and top-k (keep a few even if below threshold to avoid empty context)
        filtered = [u for u in unified if u.get("similarity_score", 0) >= 0.1]
        top_items = filtered[:12] if filtered else unified[:8]

        return {"results": top_items, "primary_document_id": primary_document_id}

    def _build_prompt(self, state: Dict[str, Any]) -> str:
        question = state.get("question", "")
        history = state.get("conversation_history") or []
        context_items = state.get("retrieval", {}).get("results", [])

        history_lines = []
        for msg in history[-3:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_lines.append(f"{role}: {msg.get('content', '')[:400].strip()}")
        history_block = "\n".join(history_lines) if history_lines else "None"

        context_lines = []
        for idx, item in enumerate(context_items, 1):
            meta = item.get("metadata", {})
            label_parts = [f"[Source {idx}]", item.get("type", "context")]
            if meta.get("document_date"):
                label_parts.append(str(meta["document_date"]))
            if meta.get("event_date"):
                label_parts.append(str(meta["event_date"]))
            header = " - ".join(label_parts)
            context_lines.append(f"{header}\n{item.get('content', '').strip()}\n")
        context_block = "\n".join(context_lines).strip() or "None"

        prompt = f"""
You are a careful medical information assistant. Answer ONLY with information supported by the provided records. Do not invent details or provide new diagnoses.

=== CONVERSATION SNAPSHOT ===
{history_block}

=== PATIENT'S MEDICAL RECORDS ===
{context_block}

=== PATIENT'S QUESTION ===
{question}

=== RESPONSE FORMAT (JSON) ===
{{
  "answer": string,
  "key_details": [string],
  "citations": [string],
  "note": string
}}
- Use [Source #] references in answer and key_details.
- If information is missing, set answer to "" and explain in note.
- Keep answer to 2-4 sentences.
"""
        return prompt.strip()

    async def _call_model(self, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = state.get("prompt", "")
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            response = await self.medgemma.generate_text_response(prompt)
            
            # Check if response is successful and has content
            if response.get("success") and (response.get("text") or response.get("structured")):
                if attempt > 0:
                    print(f"✓ LLM succeeded on retry attempt {attempt + 1}")
                return response
            
            # Log failure and retry if not last attempt
            if attempt < max_retries:
                print(f"⚠️ LLM attempt {attempt + 1} failed (no JSON), retrying...")
            else:
                print(f"❌ LLM failed after {max_retries + 1} attempts")
        
        return response  # Return last attempt even if failed

    def _normalize_output(self, state: Dict[str, Any]) -> Dict[str, Any]:
        response = state.get("response", {})
        retrieval_block = state.get("retrieval", {})
        retrieval = retrieval_block.get("results", [])
        primary_document_id = retrieval_block.get("primary_document_id")

        structured_raw = (
            response.get("structured") if isinstance(response, dict) else None
        )
        text = response.get("text") if isinstance(response, dict) else ""
        confidence = (
            response.get("confidence", 0.8) if isinstance(response, dict) else 0.8
        )

        citations = self._build_citations(retrieval, primary_document_id)

        answer_text = (
            text or "I could not generate an answer from the available records."
        )

        if structured_raw and isinstance(structured_raw, dict):
            try:
                validated = StructuredAnswer(**structured_raw)
                key_details = validated.key_details or []
                answer_text = validated.answer.strip()
                if key_details:
                    answer_text += "\nKey details:\n" + "\n".join(
                        f"- {d}" for d in key_details
                    )
                # Note field removed - no longer displayed to user
            except ValidationError:
                # fall back to raw text already set
                pass

        context_used = retrieval[:5]

        return {
            "answer": answer_text.strip(),
            "citations": citations,
            "context_used": context_used,
            "confidence": confidence,
        }

    # --- helpers ---

    def _build_citations(
        self,
        context_snippets: List[Dict[str, Any]],
        primary_document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        citations = []
        seen = set()

        # Prioritize: structured sources first, then documents
        non_doc = [s for s in context_snippets if s.get("type") != "document"]
        docs = [s for s in context_snippets if s.get("type") == "document"]

        # If we have a primary document, put it first among documents
        if primary_document_id:
            primary_docs = [
                d for d in docs if d.get("source_id") == primary_document_id
            ]
            other_docs = [d for d in docs if d.get("source_id") != primary_document_id]
            docs = primary_docs + other_docs

        # Combine: non-docs first (for answer accuracy), then top document for reference
        filtered = non_doc[:3] + docs[:2]  # Keep mix of both types

        for idx, snippet in enumerate(filtered[:8], 1):
            source_id = snippet.get("source_id")
            seen_key = (snippet.get("type"), source_id)
            if seen_key in seen:
                continue
            seen.add(seen_key)
            citations.append(
                {
                    "citation_number": idx,
                    "source_id": source_id,
                    "type": snippet.get("type"),
                    "similarity_score": snippet.get("similarity_score", 0.0),
                    "chunk_index": snippet.get("chunk_index", 0),
                    "metadata": self._augment_metadata_for_citation(snippet),
                }
            )
        return citations

    def _augment_metadata_for_citation(self, snippet: Dict[str, Any]) -> Dict[str, Any]:
        """Add helpful metadata for client-side rendering (e.g., document preview links)."""
        meta = snippet.get("metadata", {}) or {}
        if snippet.get("type") == "document":
            meta.setdefault("document_id", snippet.get("source_id"))
        return meta


def build_agentic_chat_service(medgemma_service: MedGemmaService) -> AgenticChatService:
    return AgenticChatService(medgemma=medgemma_service)
