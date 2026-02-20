"""
API v1 routes aggregation.
"""

from fastapi import APIRouter
from src.api.v1.documents import router as documents_router
from src.api.v1.clinical import router as clinical_router
from src.api.v1.files import router as files_router
from src.api.routes.chat import router as chat_router
from src.api.routes.knowledge_graph import router as knowledge_graph_router
from src.api.routes.timeline import router as timeline_router

router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(documents_router)
router.include_router(clinical_router)
router.include_router(files_router)
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(
    knowledge_graph_router, prefix="/knowledge-graph", tags=["knowledge-graph"]
)
router.include_router(timeline_router, prefix="/timeline", tags=["timeline"])
