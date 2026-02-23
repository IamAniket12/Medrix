"""
Core configuration and settings for the FastAPI application.
"""

import json
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
    google_cloud_project: str = "medrix-medgemma"
    vertex_ai_location: str = "europe-west4"
    medgemma_endpoint_id: str = "mg-endpoint-3c8c9ae8-c8f7-4f75-ac46-b4779dc43924"
    # Path to service account JSON file (local dev)
    google_application_credentials: Optional[str] = None
    # Raw JSON content of service account key (Railway / cloud deployments)
    google_application_credentials_json: Optional[str] = None

    # Colab / generic HTTP MedGemma endpoint (overrides Vertex AI when set)
    # e.g. https://xxxx.ngrok-free.app  (printed by colab_medgemma_deploy.py)
    medgemma_endpoint_url: Optional[str] = None

    # Google Cloud Storage Configuration
    gcs_bucket_name: str

    # File Upload Configuration
    max_file_size_mb: int = 10
    allowed_extensions: set = {".pdf", ".jpg", ".jpeg", ".png"}

    # CORS Settings
    cors_origins: list = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://medrix.netlify.app",
    ]
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


def get_gcp_credentials():
    """
    Load Google Cloud service-account credentials.

    Priority:
    1. GOOGLE_APPLICATION_CREDENTIALS_JSON  — raw JSON string (Railway/cloud)
    2. GOOGLE_APPLICATION_CREDENTIALS       — path to JSON file (local dev)
    3. None                                 — fall back to ADC / metadata server
    """
    from google.oauth2 import service_account

    # Option 1: JSON content provided directly (preferred for Railway)
    if settings.google_application_credentials_json:
        try:
            info = json.loads(settings.google_application_credentials_json)
            return service_account.Credentials.from_service_account_info(info)
        except Exception as e:
            print(f"[GCP] Failed to parse GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")

    # Option 2: Path to a local JSON file
    if settings.google_application_credentials:
        return service_account.Credentials.from_service_account_file(
            settings.google_application_credentials
        )

    # Option 3: Application Default Credentials (ADC)
    return None


_vertex_ai_initialized = False


def init_vertex_ai() -> None:
    """
    Initialize Vertex AI exactly once for the whole process.

    Call this from main.py startup_event so every service
    (agent_orchestrator, embeddings_service, medgemma_service) shares the
    same initialized SDK state without redundant credential loads.
    """
    global _vertex_ai_initialized
    if _vertex_ai_initialized:
        return

    from google.cloud import aiplatform

    credentials = get_gcp_credentials()
    aiplatform.init(
        project=settings.google_cloud_project,
        location=settings.vertex_ai_location,
        credentials=credentials,
    )
    _vertex_ai_initialized = True
    print(
        f"[GCP] Vertex AI initialized — project={settings.google_cloud_project} "
        f"location={settings.vertex_ai_location}"
    )
