"""Database service for basic CRUD operations."""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from ..models import Document, User


class DatabaseService:
    """Service for basic database operations."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(
        self, user_id: str, email: Optional[str] = None, name: Optional[str] = None
    ) -> User:
        """Create a new user."""
        user = User(id=user_id, email=email, name=name)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_or_create_user(
        self, user_id: str, email: Optional[str] = None, name: Optional[str] = None
    ) -> User:
        """Get existing user or create new one."""
        user = self.get_user(user_id)
        if not user:
            user = self.create_user(user_id, email, name)
        return user

    def create_document(
        self,
        document_id: str,
        user_id: str,
        filename: str,
        original_name: str,
        mime_type: str,
        file_size: int,
        file_path: str,
        document_type: Optional[str] = None,
        document_date: Optional[datetime] = None,
    ) -> Document:
        """Create a new document record."""
        document = Document(
            id=document_id,
            user_id=user_id,
            filename=filename,
            original_name=original_name,
            mime_type=mime_type,
            file_size=file_size,
            file_path=file_path,
            uploaded_at=datetime.utcnow(),
            document_type=document_type,
            document_date=document_date,
            extraction_status='pending',
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self.db.query(Document).filter(Document.id == document_id).first()

    def get_user_documents(self, user_id: str, limit: int = 50) -> List[Document]:
        """Get all documents for a user."""
        return (
            self.db.query(Document)
            .filter(Document.user_id == user_id)
            .order_by(desc(Document.uploaded_at))
            .limit(limit)
            .all()
        )

    def update_document_extraction(
        self,
        document_id: str,
        status: str,
        extracted_data: Optional[dict] = None,
    ) -> Optional[Document]:
        """Update document extraction status and data."""
        document = self.get_document(document_id)
        if document:
            document.extraction_status = status
            if extracted_data:
                document.extracted_data = extracted_data
            self.db.commit()
            self.db.refresh(document)
        return document
