"""
Medrix FastAPI Backend Application

Main application entry point for the medical document extraction API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from src.core.config import settings
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
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

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
    print(f"\n{'='*60}")
    print(f"🏥 {settings.app_name} v{settings.app_version}")
    print(f"{'='*60}")
    print(f"📡 Server running on http://{settings.host}:{settings.port}")
    print(f"📚 API Documentation: http://{settings.host}:{settings.port}/docs")
    print(f"🔌 API v1 Endpoint: http://{settings.host}:{settings.port}/api/v1")
    print(f"{'='*60}\n")


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
