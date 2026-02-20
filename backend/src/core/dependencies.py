"""
Shared dependencies for FastAPI dependency injection.
"""

from typing import Generator
from sqlalchemy.orm import Session
from src.core.config import get_settings, Settings
from src.core.database import get_db
from src.services.medgemma_service import MedGemmaService
from src.services.database_service import DatabaseService


def get_settings_dependency() -> Settings:
    """Dependency to get application settings."""
    return get_settings()


def get_medgemma_service() -> MedGemmaService:
    """Dependency to get MedGemma service instance."""
    settings = get_settings()
    return MedGemmaService(settings)


def get_database_service(db: Session = None) -> DatabaseService:
    """Dependency to get database service instance."""
    if db is None:
        # This will be injected by FastAPI when used with Depends
        db = next(get_db())
    return DatabaseService(db)
