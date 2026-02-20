"""
API routes package.
"""

from fastapi import APIRouter
from src.api.v1 import router as v1_router

router = APIRouter()

# Include versioned API routers
router.include_router(v1_router)

__all__ = ["router"]
