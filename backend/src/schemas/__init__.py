"""
Schemas package initialization.
"""

from src.schemas.document import (
    FileInfo,
    ExtractedData,
    DocumentUploadResponse,
    HealthCheck,
    ErrorResponse,
    TestResponse,
)

__all__ = [
    "FileInfo",
    "ExtractedData",
    "DocumentUploadResponse",
    "HealthCheck",
    "ErrorResponse",
    "TestResponse",
]
