"""
Medrix FastAPI Backend Application

Main application entry point for the medical document extraction API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os
import logging
import sys

from src.core.config import settings
from src.core.config import init_vertex_ai
from src.api import router
from src.schemas.document import HealthCheck

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="FastAPI backend for medical document extraction using MedGemma 1.5 4B on Google Vertex AI",
    version=settings.app_version,
    debug=settings.debug,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.netlify\.app",
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Mount uploads directory for serving PDFs
uploads_dir = os.path.join(os.getcwd(), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "api_v1": "/api/v1",
    }


@app.get("/health", response_model=HealthCheck, tags=["health"])
async def health_check():
    """Health check endpoint."""
    return HealthCheck(
        status="healthy", version=settings.app_version, timestamp=datetime.now()
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Actions to perform on application startup."""
    # Configure logging for the entire application
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set specific log levels for our application modules
    logging.getLogger("src").setLevel(logging.INFO)
    logging.getLogger("src.services").setLevel(logging.INFO)
    logging.getLogger("src.api").setLevel(logging.INFO)

    # Reduce noise from other libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    print(f"\n{'='*60}")
    print(f"[MED] {settings.app_name} v{settings.app_version}")
    print(f"{'='*60}")
    print(f"[NET] Server running on http://{settings.host}:{settings.port}")
    print(f"[DOC] API Documentation: http://{settings.host}:{settings.port}/docs")
    print(f"[API] API v1 Endpoint: http://{settings.host}:{settings.port}/api/v1")
    print(f"[LOG] Application logging configured at INFO level")
    print(f"{'='*60}\n")

    # Initialise Vertex AI once for the whole process
    init_vertex_ai()


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Actions to perform on application shutdown."""
    print("\n👋 Shutting down Medrix Backend...\n")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app", host=settings.host, port=settings.port, reload=settings.debug
    )
