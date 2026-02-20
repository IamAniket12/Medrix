"""
Core configuration and settings for the FastAPI application.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application Info
    app_name: str = "Medrix AI Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    DEBUG: bool = False  # Alias for SQLAlchemy

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Google Cloud Configuration
    google_cloud_project: str = "medrix-ai"
    vertex_ai_location: str = "europe-west4"
    medgemma_endpoint_id: str = "mg-endpoint-3c8c9ae8-c8f7-4f75-ac46-b4779dc43924"
    google_application_credentials: Optional[str] = None

    # Google Cloud Storage Configuration
    gcs_bucket_name: str

    # File Upload Configuration
    max_file_size_mb: int = 10
    allowed_extensions: set = {".pdf", ".jpg", ".jpeg", ".png"}

    # CORS Settings
    cors_origins: list = ["http://localhost:3000", "http://localhost:3001"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list = ["*"]
    cors_allow_headers: list = ["*"]

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/medrix"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export settings instance
settings = get_settings()
