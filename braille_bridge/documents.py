"""Document processing for Braille Bridge: PDF text extraction and document helpers."""
import io
import os
from typing import Dict, Any
from pypdf import PdfReader


def extract_pdf_text(stream_or_path, max_pages: int = 100) -> Dict[str, Any]:
    """Extract text from a PDF file stream (bytes/BytesIO) or file path.

    Returns a dict with:
        'text': extracted plain text,
        'pages': number of pages processed,
        'total_pages': total pages in the PDF,
        'chars': total character count,
        'is_scanned': boolean indicating if little/no text was found (suggesting scanned images)
    """
    if isinstance(stream_or_path, (bytes, bytearray)):
        stream_or_path = io.BytesIO(stream_or_path)

    try:
        reader = PdfReader(stream_or_path)
    except Exception as e:
        raise ValueError(f"Could not parse PDF: {e}")

    total_pages = len(reader.pages)
    if total_pages == 0:
        return {
            'text': '',
            'pages': 0,
            'total_pages': 0,
            'chars': 0,
            'is_scanned': False
        }

    extracted_pages = []
    num_to_read = min(total_pages, max_pages)

    for i in range(num_to_read):
        page = reader.pages[i]
        page_text = page.extract_text() or ''
        extracted_pages.append(page_text.strip())

    full_text = "\n\n".join(p for p in extracted_pages if p).strip()
    char_count = len(full_text)

    # If average characters per page is very low, it might be a scanned PDF
    is_scanned = (char_count < 20 * num_to_read)

    return {
        'text': full_text,
        'pages': num_to_read,
        'total_pages': total_pages,
        'chars': char_count,
        'is_scanned': is_scanned
    }
