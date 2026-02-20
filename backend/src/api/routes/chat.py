"""
PROPER RAG-based medical chat endpoint with industry-standard implementation.
Retrieves context from embeddings and generates answers using MedGemma.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from src.core.database import get_db
from src.services.embeddings_service import embeddings_service
from src.services.medgemma_service import MedGemmaService
from src.services.agentic_chat_service import build_agentic_chat_service
from src.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

# Initialize services
medgemma_service = MedGemmaService(settings)
agentic_chat_service = build_agentic_chat_service(medgemma_service)


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    citations: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Document citations for assistant messages"
    )


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    user_id: str = Field(..., description="User ID")
    question: str = Field(..., description="User's medical question")
    # Use default_factory to avoid shared mutable default lists.
    conversation_history: Optional[List[ChatMessage]] = Field(
        default_factory=list, description="Previous conversation messages"
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    answer: str = Field(..., description="AI-generated answer")
    citations: List[Dict[str, Any]] = Field(
        default=[], description="Source documents used"
    )
    context_used: List[Dict[str, Any]] = Field(
        default=[], description="Retrieved context snippets"
    )
    confidence: float = Field(..., description="Answer confidence score (0-1)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = Field(
        default="This information is based on your medical records and should not replace professional medical advice. Please consult your healthcare provider for medical decisions."
    )


@router.post("/ask", response_model=ChatResponse)
async def ask_medical_question(
    request: ChatRequest, db: Session = Depends(get_db)
) -> ChatResponse:
    """
    RAG-based medical Q&A endpoint.

    Flow:
    1. Query Embedding → Vector Search (documents + events + entities)
    2. Retrieve & Rerank top results
    3. Build comprehensive prompt with context
    4. Generate answer via MedGemma
    5. Return with citations

    Args:
        request: User question and conversation history
        db: Database session

    Returns:
        Answer with citations and metadata
    """
    try:
        logger.info(
            f"[RAG] Question from user {request.user_id}: {request.question[:100]}..."
        )

        logger.info(
            f"[RAG] Question from user {request.user_id}: {request.question[:100]}..."
        )

        history_payload = [msg.model_dump() for msg in request.conversation_history]

        pipeline_result = await agentic_chat_service.run(
            db=db,
            user_id=request.user_id,
            question=request.question,
            conversation_history=history_payload,
        )

        if not pipeline_result:
            logger.warning("[RAG] Agentic pipeline returned empty result")
            return ChatResponse(
                answer="I could not generate an answer from your records. Please try rephrasing or uploading more documents.",
                citations=[],
                context_used=[],
                confidence=0.0,
                timestamp=datetime.utcnow(),
            )

        return ChatResponse(
            answer=pipeline_result.get("answer", ""),
            citations=pipeline_result.get("citations", []),
            context_used=pipeline_result.get("context_used", [])[:5],
            confidence=pipeline_result.get("confidence", 0.8),
            timestamp=datetime.utcnow(),
        )

        # Search using embeddings service (Agent 5's model)
        # This returns chunk_text directly from document_embeddings table
        document_results = embeddings_service.search_similar_documents(
            db=db, user_id=user_id, query=question, limit=top_k
        )

        # Build results with the embedded chunk_text
        all_results = []
        for doc in document_results:
            all_results.append(
                {
                    "type": "document",
                    "source_id": doc["document_id"],
                    "embedding_id": doc["embedding_id"],
                    "content": doc[
                        "chunk_text"
                    ],  # This is the actual embedded content!
                    "chunk_index": doc["chunk_index"],
                    "metadata": {
                        "document_type": doc.get("document_type"),
                        "document_date": doc.get("document_date"),
                        "filename": doc.get("filename"),
                        "original_name": doc.get("original_name"),
                    },
                    "similarity_score": doc["similarity_score"],
                }
            )

        has_data = len(all_results) > 0
        avg_similarity = (
            sum(r["similarity_score"] for r in all_results) / len(all_results)
            if has_data
            else 0.0
        )

        return {
            "has_data": has_data,
            "context_snippets": all_results,
            "statistics": {
                "total_results": len(all_results),
                "document_results": len(document_results),
                "avg_similarity": avg_similarity,
            },
        }

    except Exception as e:
        logger.error(f"[RAG Retrieval] Error: {str(e)}", exc_info=True)
        raise


def build_comprehensive_prompt(
    question: str,
    context_snippets: List[Dict[str, Any]],
    conversation_history: Optional[List[ChatMessage]] = None,
) -> str:
    """
    Build an agentic-style prompt for MedGemma with structured context.

    - Defines the assistant role and strict evidence-only constraint
    - Preserves limited conversation state for continuity
    - Presents context with numbered sources and metadata
    - Requests short, cited answers with an explicit template
    - Encourages reasoning while keeping the final reply concise
    """

    def format_history(history: List[ChatMessage]) -> str:
        """Serialize the last few turns to keep continuity without overflowing tokens."""
        if not history:
            return "None"
        trimmed = []
        for msg in history[-3:]:
            role = "User" if msg.role == "user" else "Assistant"
            trimmed.append(f"{role}: {msg.content[:400].strip()}")
        return "\n".join(trimmed)

    def format_context(snippets: List[Dict[str, Any]]) -> str:
        """Render a compact, source-numbered context block."""
        lines = []
        for idx, snippet in enumerate(snippets[:5], 1):
            metadata = snippet.get("metadata", {})
            doc_date = metadata.get("document_date")
            date_str = f" ({doc_date})" if doc_date else ""
            header = f"[Source {idx}]{date_str}"
            content = snippet.get("content", "").strip()
            lines.append(f"{header}\n{content}\n")
        return "\n".join(lines).strip()

    history_block = format_history(conversation_history or [])
    context_block = format_context(context_snippets)

    # Structured prompt with explicit markers helps both the model and the mock path
    prompt = f"""
You are a careful medical information assistant. Answer ONLY with information supported by the provided records. Do not invent details, and do not offer diagnosis or treatment beyond what is stated.

=== CONVERSATION SNAPSHOT ===
{history_block}

=== PATIENT'S MEDICAL RECORDS ===
{context_block}

=== PATIENT'S QUESTION ===
{question}

=== INSTRUCTIONS ===
- Think briefly about the key facts from the sources. Do not include your reasoning in the final answer.
- If the records are insufficient to answer, say so clearly and suggest what information is missing.
- Keep the answer concise (2-4 sentences) and cite sources using [Source #].
- Include critical details (dates, dosages, values) when available.

=== RESPONSE FORMAT ===
Answer: <2-3 sentence answer with [Source #] citations>
Key details: <bullet-style facts with citations>
Note: This information is for educational purposes and not a substitute for professional medical advice.

Your response:
"""

    return prompt.strip()


def build_citations(context_snippets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build comprehensive citation list from retrieved documents.
    Includes all necessary metadata for frontend display and verification.

    Args:
        context_snippets: Retrieved document context with embeddings

    Returns:
        List of document citations with complete metadata
    """
    citations = []
    seen_sources = set()  # Track by document_id to avoid duplicates

    for idx, snippet in enumerate(context_snippets[:8], 1):  # Top 8 sources
        source_id = snippet["source_id"]

        # Avoid duplicate documents (same document may have multiple chunks)
        if source_id in seen_sources:
            continue
        seen_sources.add(source_id)

        citation = {
            "citation_number": idx,
            "source_id": source_id,
            "embedding_id": snippet.get("embedding_id"),
            "type": snippet["type"],
            "similarity_score": snippet["similarity_score"],
            "chunk_index": snippet.get("chunk_index", 0),
            # Document metadata for display
            "metadata": {
                "filename": snippet["metadata"].get("filename", "Unknown"),
                "original_name": snippet["metadata"].get("original_name"),
                "document_type": snippet["metadata"].get("document_type", "document"),
                "document_date": snippet["metadata"].get("document_date"),
            },
            # User-friendly display fields
            "title": snippet["metadata"].get("filename", "Unknown Document"),
            "document_type": snippet["metadata"].get("document_type", "document"),
            "date": snippet["metadata"].get("document_date"),
            "relevance": f"{snippet['similarity_score']:.0%}",
        }

        citations.append(citation)

    return citations
