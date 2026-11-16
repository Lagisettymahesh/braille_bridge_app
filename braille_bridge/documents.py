"""Document processing for Braille Bridge: PDF text extraction and document helpers."""
import io
import os
from typing import Dict, Any
from pypdf import PdfReader


def extract_pdf_text(
    stream_or_path,
    max_pages: int = 100,
    ocr_fallback: bool = True,
    ocr_lang: str = 'eng'
) -> Dict[str, Any]:
    """Extract text from a PDF file stream (bytes/BytesIO) or file path.

    Supports both text-based PDFs and image-based (scanned) PDFs via OCR fallback.
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
            'is_scanned': False,
            'method': 'empty'
        }

    extracted_pages = []
    num_to_read = min(total_pages, max_pages)

    for i in range(num_to_read):
        page = reader.pages[i]
        try:
            page_text = page.extract_text() or ''
        except Exception:
            page_text = ''
        extracted_pages.append(page_text.strip())

    full_text = "\n\n".join(p for p in extracted_pages if p).strip()
    char_count = len(full_text)
    is_scanned = (char_count < 15 * num_to_read)
    method = 'digital'

    # If little or no digital text was found, attempt OCR on embedded page images
    if is_scanned and ocr_fallback:
        ocr_text_parts = []
        try:
            import ocr
            if ocr.status().get('available'):
                for i in range(num_to_read):
                    page = reader.pages[i]
                    for img_obj in page.images:
                        try:
                            t = ocr.read_text(img_obj.data, ocr_lang)
                            if t and t.strip():
                                ocr_text_parts.append(t.strip())
                        except Exception:
                            pass
        except Exception:
            pass

        if ocr_text_parts:
            full_text = "\n\n".join(ocr_text_parts).strip()
            char_count = len(full_text)
            method = 'ocr_scanned'
            is_scanned = False

    return {
        'text': full_text,
        'pages': num_to_read,
        'total_pages': total_pages,
        'chars': char_count,
        'is_scanned': is_scanned,
        'method': method
    }
