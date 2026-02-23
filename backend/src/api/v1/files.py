"""File serving endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from google.cloud import storage
from datetime import timedelta

from src.core.config import settings, get_gcp_credentials

router = APIRouter(prefix="/files", tags=["files"])


def get_gcs_client():
    """
    Initialize GCS client using centralized credential loading.
    Supports both GOOGLE_APPLICATION_CREDENTIALS_JSON (Railway/cloud)
    and GOOGLE_APPLICATION_CREDENTIALS file path (local dev).
    """
    credentials = get_gcp_credentials()

    if credentials is None:
        # Fall back to Application Default Credentials
        return storage.Client(project=settings.google_cloud_project)

    # Add GCS scope if not already present
    from google.auth.transport.requests import Request
    import google.auth

    scoped = (
        credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
        if hasattr(credentials, "with_scopes")
        else credentials
    )

    return storage.Client(credentials=scoped, project=settings.google_cloud_project)


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

        # Redirect to the signed URL so the PDF opens directly
        return RedirectResponse(url=url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
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
