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
logger.info("[CHAT Router] Initializing MedGemma service...")
medgemma_service = MedGemmaService(settings)
logger.info("[CHAT Router] Building agentic chat service...")
agentic_chat_service = build_agentic_chat_service(medgemma_service)
logger.info("[CHAT Router] Chat services initialized and ready")


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
        logger.info("=" * 80)
        logger.info(f"[RAG CHAT] New question from user: {request.user_id}")
        logger.info(f"[RAG CHAT] Question: {request.question}")
        logger.info(
            f"[RAG CHAT] Conversation history: {len(request.conversation_history)} messages"
        )
        logger.info("=" * 80)

        history_payload = [msg.model_dump() for msg in request.conversation_history]

        # Run the agentic RAG pipeline
        pipeline_result = await agentic_chat_service.run(
            db=db,
            user_id=request.user_id,
            question=request.question,
            conversation_history=history_payload,
        )

        # Log the full result for debugging
        logger.info("=" * 80)
        logger.info(f"[RAG CHAT] Pipeline Result:")
        logger.info(
            f"[RAG CHAT] Answer length: {len(pipeline_result.get('answer', ''))} chars"
        )
        logger.info(f"[RAG CHAT] Answer: {pipeline_result.get('answer', 'NO ANSWER')}")
        logger.info(
            f"[RAG CHAT] Citations: {len(pipeline_result.get('citations', []))} sources"
        )
        logger.info(
            f"[RAG CHAT] Context used: {len(pipeline_result.get('context_used', []))} items"
        )
        logger.info(f"[RAG CHAT] Confidence: {pipeline_result.get('confidence', 0.0)}")
        logger.info("=" * 80)

        if not pipeline_result or not pipeline_result.get("answer"):
            logger.warning("[RAG CHAT] Pipeline returned empty or no answer")
            return ChatResponse(
                answer="I could not generate an answer from your records. Please try rephrasing your question or uploading more medical documents.",
                citations=[],
                context_used=[],
                confidence=0.0,
                timestamp=datetime.utcnow(),
            )

        response = ChatResponse(
            answer=pipeline_result.get("answer", ""),
            citations=pipeline_result.get("citations", []),
            context_used=pipeline_result.get("context_used", [])[:5],
            confidence=pipeline_result.get("confidence", 0.8),
            timestamp=datetime.utcnow(),
        )

        logger.info(f"[RAG CHAT] ✅ Successfully generated response")
        return response

    except Exception as e:
        logger.error(
            f"[RAG CHAT] ❌ Error processing question: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to process question: {str(e)}"
        )
