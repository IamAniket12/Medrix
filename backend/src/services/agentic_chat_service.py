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
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ValidationError

from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from src.services.medgemma_service import MedGemmaService
from src.services.embeddings_service import embeddings_service

# Module-level logger
logger = logging.getLogger(__name__)


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
        logger.info("[RAG Service] AgenticChatService initialized")

    async def run(
        self,
        db: Any,
        user_id: str,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        logger.info(f"[RAG Service] Starting RAG pipeline for user: {user_id}")
        base_state = {
            "db": db,
            "user_id": user_id,
            "question": question.strip(),
            "conversation_history": conversation_history or [],
        }
        result = await self.chain.ainvoke(base_state)
        logger.info(f"[RAG Service] Pipeline complete")
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

        logger.info(
            f"[RAG Retrieval] Starting context retrieval for question: {question[:100]}..."
        )

        # Structured context (active meds/conditions/events) for precise answers like start dates
        patient_context = embeddings_service.get_patient_context(
            db=db, user_id=user_id, current_document_date=None, limit=20
        )
        logger.info(
            f"[RAG Retrieval] Patient context: {len(patient_context.get('active_medications', []))} active meds, {len(patient_context.get('conditions', []))} conditions"
        )

        # Documents
        doc_hits = embeddings_service.search_similar_documents(
            db=db, user_id=user_id, query=question, limit=12
        )
        logger.info(f"[RAG Retrieval] Found {len(doc_hits)} similar documents")

        # Timeline events (often contain start dates)
        event_hits = embeddings_service.search_similar_timeline_events(
            db=db, user_id=user_id, query=question, limit=8
        )
        logger.info(f"[RAG Retrieval] Found {len(event_hits)} timeline events")

        # Clinical entities (meds/conditions/labs) for direct lookups
        entity_hits = embeddings_service.search_similar_clinical_entities(
            db=db, user_id=user_id, query=question, limit=8
        )
        logger.info(f"[RAG Retrieval] Found {len(entity_hits)} clinical entities")

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

        logger.info(f"[RAG Retrieval] Total unified results: {len(unified)}")
        logger.info(f"[RAG Retrieval] After filtering: {len(filtered)} items")
        logger.info(f"[RAG Retrieval] Final top items: {len(top_items)} items")

        # Log top results for debugging
        for idx, item in enumerate(top_items[:3], 1):
            logger.info(
                f"[RAG Retrieval] Top {idx}: type={item.get('type')}, score={item.get('similarity_score'):.3f}, content_preview={item.get('content', '')[:80]}..."
            )

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
You are an expert medical information assistant that helps patients understand their medical records. Your role is to:
- Answer questions ONLY using information from the provided medical records
- Cite all information with [Source #] references
- Be precise with medical facts (dates, dosages, values, conditions)
- Never invent or assume information not in the records
- If information is missing, clearly state what is unavailable

=== RECENT CONVERSATION ===
{history_block}

=== AVAILABLE MEDICAL RECORDS ===
{context_block}

=== PATIENT'S QUESTION ===
{question}

=== INSTRUCTIONS ===
1. Review all sources carefully and identify relevant information
2. Answer the question using ONLY the facts from the sources above
3. Include specific details: dates, dosages, values, test results, diagnoses
4. Cite every fact with [Source #] references
5. If the question cannot be fully answered from these records, explain what information is missing
6. Keep your answer concise (2-5 sentences) but include all critical medical details
7. Format your response as valid JSON

=== RESPONSE FORMAT (JSON) ===
{{
  "answer": "<Your answer here with [Source #] citations>",
  "key_details": [
    "<Key fact 1 with [Source #]>",
    "<Key fact 2 with [Source #]>"
  ],
  "citations": ["Source 1", "Source 2"],
  "note": "<Any clarifications or limitations>"
}}

**Your response (JSON only):**
"""
        return prompt.strip()

    async def _call_model(self, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = state.get("prompt", "")
        question = state.get("question", "")
        max_retries = 2

        logger.info(f"[RAG Model Call] Question: {question[:150]}...")
        logger.info(f"[RAG Model Call] Prompt length: {len(prompt)} chars")

        for attempt in range(max_retries + 1):
            logger.info(f"[RAG Model Call] Attempt {attempt + 1}/{max_retries + 1}")
            response = await self.medgemma.generate_text_response(prompt)

            # Log detailed response for debugging
            logger.info(f"[RAG Model Response] Success: {response.get('success')}")
            if response.get("text"):
                logger.info(
                    f"[RAG Model Response] Text length: {len(response.get('text', ''))} chars"
                )
                logger.info(
                    f"[RAG Model Response] Text preview: {response.get('text', '')[:300]}..."
                )
            if response.get("structured"):
                logger.info(
                    f"[RAG Model Response] Structured: {response.get('structured')}"
                )
            if not response.get("success"):
                logger.warning(f"[RAG Model Response] Error: {response.get('error')}")

            # Check if response is successful and has content
            if response.get("success") and (
                response.get("text") or response.get("structured")
            ):
                logger.info(f"✅ [RAG Model Call] Success on attempt {attempt + 1}")
                return response

            # Log failure and retry if not last attempt
            if attempt < max_retries:
                logger.warning(
                    f"⚠️ [RAG Model Call] Attempt {attempt + 1} failed, retrying..."
                )
                await asyncio.sleep(1)  # Brief delay before retry
            else:
                logger.error(
                    f"❌ [RAG Model Call] All {max_retries + 1} attempts failed"
                )
                logger.error(f"[RAG Model Call] Final response: {response}")

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
    logger.info("[RAG Service] Building agentic chat service")
    service = AgenticChatService(medgemma=medgemma_service)
    logger.info("[RAG Service] Agentic chat service ready")
    return service
