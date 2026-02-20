"""File serving endpoints."""

from fastapi import APIRouter, HTTPException
from google.cloud import storage
from google.oauth2 import service_account
from datetime import timedelta
import os

from src.core.config import settings

router = APIRouter(prefix="/files", tags=["files"])


def get_gcs_client():
    """
    Initialize GCS client with explicit credentials.
    Enterprise best practice: Explicit credential management.
    """
    credentials_path = settings.google_application_credentials

    if not credentials_path:
        raise ValueError(
            "GOOGLE_APPLICATION_CREDENTIALS not configured in settings. "
            "Please set it in your .env file."
        )

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"Service account file not found at: {credentials_path}"
        )

    # Explicitly load credentials from service account file
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )

    # Initialize client with explicit credentials
    return storage.Client(
        credentials=credentials, project=settings.google_cloud_project
    )


@router.get("/view/{file_path:path}")
async def get_file_url(file_path: str):
    """
    Generate a signed URL for secure file access from GCS.

    Enterprise approach:
    1. Explicit credential loading (not implicit)
    2. Signed URLs with expiration (security)
    3. Proper error handling with details
    4. Service account with minimal permissions (IAM best practice)

    Returns a temporary URL (valid for 1 hour) to view the file.
    """
    try:
        # Get authenticated GCS client
        storage_client = get_gcs_client()
        bucket = storage_client.bucket(settings.gcs_bucket_name)
        blob = bucket.blob(file_path)

        # Check if file exists (avoid unnecessary signed URL generation)
        if not blob.exists():
            raise HTTPException(
                status_code=404, detail=f"File not found in bucket: {file_path}"
            )

        # Generate signed URL with v4 signing (most secure)
        # Enterprise practice: Short-lived tokens (1 hour)
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET",
        )

        return {
            "success": True,
            "url": url,
            "expires_in": 3600,  # seconds
            "file_path": file_path,
        }

    except HTTPException:
        raise
    except ValueError as e:
        # Configuration error
        print(f"❌ Configuration Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "GCS credentials not configured",
                "message": str(e),
                "action": "Set GOOGLE_APPLICATION_CREDENTIALS environment variable",
            },
        )
    except FileNotFoundError as e:
        # Credentials file missing
        print(f"❌ Credentials File Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Service account file not found",
                "message": str(e),
                "action": "Check GOOGLE_APPLICATION_CREDENTIALS path",
            },
        )
    except Exception as e:
        # Unexpected error
        print(f"❌ GCS Error: {str(e)}")
        print(f"   File path: {file_path}")
        print(f"   Bucket: {settings.gcs_bucket_name}")

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to generate signed URL",
                "message": str(e),
                "file_path": file_path,
                "bucket": settings.gcs_bucket_name,
            },
        )
