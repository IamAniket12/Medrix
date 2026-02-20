"""
Convert all test PDFs to PNG images for testing.
Processes multi-page PDFs by vertically stitching all pages into a single image.
"""

import os
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image


def convert_pdf_to_image(pdf_path: Path, output_format: str = "png", dpi: int = 200):
    """
    Convert a PDF to a single image.
    For multi-page PDFs, vertically stitches all pages together.

    Args:
        pdf_path: Path to the PDF file
        output_format: Output format ('png' or 'jpeg')
        dpi: Resolution for conversion (higher = better quality but larger file)

    Returns:
        Path to the created image file
    """
    print(f"Converting {pdf_path.name}...")

    # Convert PDF to images
    images = convert_from_path(str(pdf_path), dpi=dpi)

    if len(images) == 1:
        # Single page - just save it
        output_path = pdf_path.with_suffix(f".{output_format}")
        images[0].save(output_path, output_format.upper())
        print(f"  ✓ Created single-page image: {output_path.name}")
    else:
        # Multiple pages - stitch vertically
        total_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)

        # Create a new image with combined height
        stitched = Image.new("RGB", (total_width, total_height), "white")

        # Paste each page
        y_offset = 0
        for img in images:
            # Center horizontally if needed
            x_offset = (total_width - img.width) // 2
            stitched.paste(img, (x_offset, y_offset))
            y_offset += img.height

        # Save stitched image
        output_path = pdf_path.with_suffix(f".{output_format}")
        stitched.save(output_path, output_format.upper())
        print(f"  ✓ Stitched {len(images)} pages into: {output_path.name}")

    return output_path


def main():
    """Convert all PDFs in test_data directory to images."""
    # Get the test_data directory
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    test_data_dir = backend_dir / "test_data"

    if not test_data_dir.exists():
        print(f"Error: test_data directory not found at {test_data_dir}")
        return

    # Find all PDF files recursively
    pdf_files = list(test_data_dir.rglob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in test_data directory")
        return

    print(f"\nFound {len(pdf_files)} PDF file(s) to convert")
    print("=" * 60)

    # Convert each PDF
    converted_files = []
    for pdf_path in pdf_files:
        try:
            output_path = convert_pdf_to_image(pdf_path, output_format="png", dpi=200)
            converted_files.append(output_path)
        except Exception as e:
            print(f"  ✗ Error converting {pdf_path.name}: {str(e)}")

    print("=" * 60)
    print(f"\n✓ Successfully converted {len(converted_files)} PDF(s) to PNG images")

    # Optional: Ask if user wants to delete original PDFs
    print("\nOriginal PDF files are still present.")
    delete = input("Delete original PDF files? (y/n): ").strip().lower()

    if delete == "y":
        for pdf_path in pdf_files:
            try:
                pdf_path.unlink()
                print(f"  ✓ Deleted {pdf_path.name}")
            except Exception as e:
                print(f"  ✗ Error deleting {pdf_path.name}: {str(e)}")
        print("\n✓ Cleanup complete")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PDF to Image Converter for Test Data")
    print("=" * 60)
    main()
