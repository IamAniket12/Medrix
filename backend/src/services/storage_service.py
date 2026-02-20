"""
Cloud storage service for handling file uploads to Google Cloud Storage.
"""

import os
from typing import Optional, BinaryIO
from google.cloud import storage
from google.oauth2 import service_account
from src.core.config import Settings
from src.utils.file_utils import generate_unique_filename


class StorageService:
    """Service for managing file storage in Google Cloud Storage."""

    def __init__(self, settings: Settings):
        """
        Initialize storage service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.bucket_name = settings.gcs_bucket_name
        self.client = None
        self.bucket = None
        self._initialized = False

        self._init_gcs()

    def _init_gcs(self) -> None:
        """
        Initialize Google Cloud Storage with explicit credentials.
        Enterprise best practice: Explicit credential management.
        """
        try:
            if not self.bucket_name:
                raise ValueError("GCS_BUCKET_NAME not configured in .env")

            # Get credentials path
            credentials_path = self.settings.google_application_credentials
            if not credentials_path:
                raise ValueError(
                    "GOOGLE_APPLICATION_CREDENTIALS not configured in .env"
                )

            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"Service account file not found at: {credentials_path}"
                )

            # Explicitly load credentials from service account file
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

            # Initialize client with explicit credentials
            self.client = storage.Client(
                credentials=credentials, project=self.settings.google_cloud_project
            )
            self.bucket = self.client.bucket(self.bucket_name)

            # Test if bucket exists
            if not self.bucket.exists():
                raise ValueError(f"Bucket '{self.bucket_name}' does not exist")

            self._initialized = True
            print(f"✓ Google Cloud Storage initialized: {self.bucket_name}")
            print(f"✓ Using service account: {credentials_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google Cloud Storage: {e}")

    async def save_file(
        self, file_content: BinaryIO, original_filename: str, folder: str = "documents"
    ) -> dict:
        """
        Save file to Google Cloud Storage.

        Args:
            file_content: File content as binary stream
            original_filename: Original name of the file
            folder: Subfolder to organize files

        Returns:
            Dictionary with file information
        """
        # Generate unique filename
        unique_filename = generate_unique_filename(original_filename)
        file_path = f"{folder}/{unique_filename}"

        return await self._save_to_gcs(file_content, file_path, original_filename)

    async def _save_to_gcs(
        self, file_content: BinaryIO, file_path: str, original_filename: str
    ) -> dict:
        """Save file to Google Cloud Storage."""
        try:
            blob = self.bucket.blob(file_path)

            # Upload file (read synchronously, not async)
            content = file_content.read()
            blob.upload_from_string(content)

            # Make file publicly readable (optional - remove if you want private)
            # blob.make_public()

            return {
                "success": True,
                "storage_mode": "gcs",
                "file_path": file_path,
                "bucket": self.bucket_name,
                "original_filename": original_filename,
                "url": f"gs://{self.bucket_name}/{file_path}",
                "public_url": blob.public_url if blob.public_url else None,
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to upload to GCS: {str(e)}"}

    async def get_file(self, file_path: str) -> Optional[bytes]:
        """
        Retrieve file content from Google Cloud Storage.

        Args:
            file_path: Path to the file

        Returns:
            File content as bytes, or None if not found
        """
        return await self._get_from_gcs(file_path)

    async def _get_from_gcs(self, file_path: str) -> Optional[bytes]:
        """Get file from Google Cloud Storage."""
        try:
            blob = self.bucket.blob(file_path)

            if not blob.exists():
                return None

            return blob.download_as_bytes()
        except Exception as e:
            print(f"Error retrieving file from GCS: {e}")
            return None

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete file from Google Cloud Storage.

        Args:
            file_path: Path to the file

        Returns:
            True if deleted successfully, False otherwise
        """
        return await self._delete_from_gcs(file_path)

    async def _delete_from_gcs(self, file_path: str) -> bool:
        """Delete file from Google Cloud Storage."""
        try:
            blob = self.bucket.blob(file_path)

            if blob.exists():
                blob.delete()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file from GCS: {e}")
            return False

    def get_file_url(self, file_path: str) -> str:
        """
        Get GCS URL for accessing the file.

        Args:
            file_path: Path to the file

        Returns:
            GCS URL string
        """
        return f"gs://{self.bucket_name}/{file_path}"
