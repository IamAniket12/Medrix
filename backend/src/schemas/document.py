"""
Pydantic schemas for request/response models.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


# File Upload Schemas
class FileInfo(BaseModel):
    """File information schema."""

    original_filename: str
    saved_filename: str
    file_size: str
    file_type: str
    upload_timestamp: Optional[datetime] = None


class ExtractedData(BaseModel):
    """Extracted medical data schema from multi-agent system."""

    raw_output: Optional[Dict[str, Any]] = None
    text: str = ""
    labels: List[str] = []
    summary: str = ""
    confidence_score: Optional[float] = None

    # Multi-agent specific fields
    classification: Optional[Dict[str, Any]] = None
    medical_data: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload."""

    success: bool
    message: str
    file_info: FileInfo
    extracted_data: Optional[ExtractedData] = None


# Health Check Schema
class HealthCheck(BaseModel):
    """Health check response schema."""

    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)


# Error Schema
class ErrorResponse(BaseModel):
    """Error response schema."""

    success: bool = False
    error: str
    detail: Optional[str] = None
    status_code: int


# Test Endpoint Schema
class TestResponse(BaseModel):
    """Test endpoint response schema."""

    status: str
    message: str
    config: Dict[str, Any]
