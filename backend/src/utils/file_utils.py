"""
File handling utilities.
"""

import os
import uuid
from pathlib import Path
from typing import Set


def generate_unique_filename(original_filename: str) -> str:
    """
    Generate a unique filename using UUID.

    Args:
        original_filename: Original name of the file

    Returns:
        Unique filename with original extension
    """
    extension = Path(original_filename).suffix
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{extension}"


def ensure_upload_dir(upload_dir: str) -> None:
    """
    Ensure upload directory exists.

    Args:
        upload_dir: Path to the upload directory
    """
    os.makedirs(upload_dir, exist_ok=True)


def get_file_extension(filename: str) -> str:
    """
    Get file extension in lowercase.

    Args:
        filename: Name of the file

    Returns:
        File extension (e.g., '.pdf', '.jpg')
    """
    return Path(filename).suffix.lower()


def is_allowed_file(filename: str, allowed_extensions: Set[str]) -> bool:
    """
    Check if file extension is allowed.

    Args:
        filename: Name of the file
        allowed_extensions: Set of allowed extensions

    Returns:
        True if file type is allowed, False otherwise
    """
    return get_file_extension(filename) in allowed_extensions


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted string (e.g., '2.45 MB')
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"
