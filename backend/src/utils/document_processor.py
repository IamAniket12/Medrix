"""
Document processing utilities for PDFs and images.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from PIL import Image


class DocumentProcessor:
    """Utility class for processing medical documents (PDFs and images)."""

    @staticmethod
    def is_pdf(file_path: str) -> bool:
        """
        Check if file is a PDF.

        Args:
            file_path: Path to the file

        Returns:
            True if file is PDF, False otherwise
        """
        return file_path.lower().endswith(".pdf")

    @staticmethod
    def is_image(file_path: str) -> bool:
        """
        Check if file is an image.

        Args:
            file_path: Path to the file

        Returns:
            True if file is an image, False otherwise
        """
        image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
        return any(file_path.lower().endswith(ext) for ext in image_extensions)

    @staticmethod
    def pdf_to_images(pdf_path: str, output_dir: Optional[str] = None) -> List[str]:
        """
        Convert PDF pages to images.

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save images (defaults to PDF directory)

        Returns:
            List of paths to generated images
        """
        if output_dir is None:
            output_dir = os.path.dirname(pdf_path)

        # Convert PDF to images
        images = convert_from_path(pdf_path)

        image_paths = []
        base_name = Path(pdf_path).stem

        for i, image in enumerate(images):
            image_path = os.path.join(output_dir, f"{base_name}_page_{i+1}.png")
            image.save(image_path, "PNG")
            image_paths.append(image_path)

        return image_paths

    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """
        Extract text content from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text string
        """
        try:
            reader = PdfReader(pdf_path)
            text = ""

            for page in reader.pages:
                text += page.extract_text() + "\n"

            return text.strip()
        except Exception as e:
            return f"Error extracting text: {str(e)}"

    @staticmethod
    def resize_image(image_path: str, max_size: tuple = (1024, 1024)) -> str:
        """
        Resize image to fit within max_size while maintaining aspect ratio.

        Args:
            image_path: Path to image file
            max_size: Maximum (width, height) tuple

        Returns:
            Path to resized image
        """
        try:
            with Image.open(image_path) as img:
                # Calculate new size maintaining aspect ratio
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

                # Save resized image
                resized_path = image_path.replace(
                    Path(image_path).suffix, f"_resized{Path(image_path).suffix}"
                )
                img.save(resized_path)

                return resized_path
        except Exception as e:
            print(f"Error resizing image: {e}")
            return image_path

    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """
        Get basic file information.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file metadata
        """
        stat = os.stat(file_path)
        return {
            "filename": os.path.basename(file_path),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "extension": Path(file_path).suffix,
            "is_pdf": DocumentProcessor.is_pdf(file_path),
            "is_image": DocumentProcessor.is_image(file_path),
        }
