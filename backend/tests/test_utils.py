"""
Test utility functions.
"""

from src.utils.file_utils import (
    generate_unique_filename,
    get_file_extension,
    is_allowed_file,
    format_file_size,
)


def test_generate_unique_filename():
    """Test unique filename generation."""
    filename1 = generate_unique_filename("test.pdf")
    filename2 = generate_unique_filename("test.pdf")
    assert filename1 != filename2
    assert filename1.endswith(".pdf")


def test_get_file_extension():
    """Test file extension extraction."""
    assert get_file_extension("test.pdf") == ".pdf"
    assert get_file_extension("Test.PDF") == ".pdf"
    assert get_file_extension("file.JPG") == ".jpg"


def test_is_allowed_file():
    """Test file extension validation."""
    allowed = {".pdf", ".jpg", ".png"}
    assert is_allowed_file("test.pdf", allowed) is True
    assert is_allowed_file("test.jpg", allowed) is True
    assert is_allowed_file("test.txt", allowed) is False


def test_format_file_size():
    """Test file size formatting."""
    assert format_file_size(500) == "500.00 B"
    assert format_file_size(1024) == "1.00 KB"
    assert format_file_size(1048576) == "1.00 MB"
