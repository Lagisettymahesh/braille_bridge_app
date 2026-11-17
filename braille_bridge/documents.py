"""Document processing for Braille Bridge: PDF text extraction, OCR fallback, and document search."""
import io
import os
import glob
import re
from typing import Dict, Any, List, Optional
from pypdf import PdfReader


def parse_page_range(range_str: str, total_pages: int) -> List[int]:
    """Parse page range string (e.g. 'all', '1-3', '2,4', '1-2, 5') into 0-based page indices.

    Safely bounds all indices between 0 and total_pages - 1.
    If empty, 'all', or invalid, defaults to all pages.
    """
    if not range_str or str(range_str).strip().lower() in ('all', '*', ''):
        return list(range(total_pages))

    indices = set()
    parts = str(range_str).split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            try:
                tokens = [t.strip() for t in part.split('-') if t.strip()]
                if len(tokens) == 2:
                    start = max(1, int(tokens[0]))
                    end = min(total_pages, int(tokens[1]))
                    for p in range(start, end + 1):
                        indices.add(p - 1)
                elif len(tokens) == 1:
                    p = int(tokens[0])
                    if 1 <= p <= total_pages:
                        indices.add(p - 1)
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if 1 <= p <= total_pages:
                    indices.add(p - 1)
            except ValueError:
                continue

    result = sorted(indices)
    return result if result else list(range(total_pages))


def extract_pdf_text(
    stream_or_path,
    page_range: str = 'all',
    max_pages: int = 200,
    ocr_fallback: bool = True,
    ocr_lang: str = 'eng'
) -> Dict[str, Any]:
    """Extract text from a PDF file stream (bytes/BytesIO) or file path.

    Supports:
    - Text-based multi-page PDFs
    - Selected page ranges ('1-3', '2,5', 'all')
    - Scanned/image-based PDFs via OCR fallback
    - Encrypted / password-protected PDF detection
    - Corrupted PDF handling with clean error messages
    """
    if isinstance(stream_or_path, (bytes, bytearray)):
        if not stream_or_path.startswith(b'%PDF-'):
            raise ValueError("Invalid PDF format: File header does not match PDF signature (%PDF-).")
        stream_or_path = io.BytesIO(stream_or_path)

    try:
        reader = PdfReader(stream_or_path)
    except Exception as e:
        raise ValueError(f"Could not parse PDF document: {e}")

    # Check for encryption
    if getattr(reader, 'is_encrypted', False):
        try:
            # Try blank password
            decrypt_res = reader.decrypt('')
            if decrypt_res == 0:
                raise ValueError("PDF is password-protected. Please provide an unlocked document.")
        except Exception:
            raise ValueError("PDF is password-protected. Please provide an unlocked document.")

    try:
        total_pages = len(reader.pages)
    except Exception as e:
        raise ValueError(f"Failed to read PDF pages: {e}")

    if total_pages == 0:
        return {
            'text': '',
            'pages': 0,
            'total_pages': 0,
            'chars': 0,
            'is_scanned': False,
            'method': 'empty',
            'warning': None,
            'pages_detail': []
        }

    # Determine pages to extract
    target_indices = parse_page_range(page_range, total_pages)
    if max_pages and len(target_indices) > max_pages:
        target_indices = target_indices[:max_pages]

    extracted_pages = []
    pages_detail = []

    for idx in target_indices:
        try:
            page = reader.pages[idx]
            page_text = page.extract_text() or ''
        except Exception:
            page_text = ''
        cleaned = page_text.strip()
        extracted_pages.append(cleaned)
        pages_detail.append({
            'page': idx + 1,
            'chars': len(cleaned),
            'has_text': bool(cleaned)
        })

    full_text = "\n\n".join(p for p in extracted_pages if p).strip()
    char_count = len(full_text)
    num_read = len(target_indices)
    is_scanned = (char_count < 20 * num_read)
    method = 'digital'
    warning = None

    # Fallback to OCR on embedded page images if little or no digital text found
    if is_scanned and ocr_fallback:
        ocr_text_parts = []
        try:
            import ocr
            if ocr.status().get('available'):
                for idx in target_indices:
                    page = reader.pages[idx]
                    page_ocr_parts = []
                    for img_obj in page.images:
                        try:
                            t = ocr.read_text(img_obj.data, ocr_lang)
                            if t and t.strip():
                                page_ocr_parts.append(t.strip())
                        except Exception:
                            pass
                    if page_ocr_parts:
                        ocr_text_parts.append("\n".join(page_ocr_parts))
        except Exception:
            pass

        if ocr_text_parts:
            full_text = "\n\n".join(ocr_text_parts).strip()
            char_count = len(full_text)
            method = 'ocr_scanned'
            is_scanned = False
            if char_count < 30 * num_read:
                warning = "OCR extracted sparse text. Document image resolution or contrast may be low."
        else:
            warning = "Document contains no selectable text and OCR found no readable characters."

    return {
        'text': full_text,
        'pages': num_read,
        'total_pages': total_pages,
        'chars': char_count,
        'is_scanned': is_scanned,
        'method': method,
        'warning': warning,
        'pages_detail': pages_detail,
        'page_range': page_range
    }


def find_local_pdfs(folder_name: str = '', query: str = '', max_results: int = 20) -> List[Dict[str, Any]]:
    """Search for PDF files on the user's system matching a given folder name and/or search query.

    Handles standard Windows folders, OneDrive redirects, and subdirectories.
    """
    home = os.path.expanduser('~')
    folder_map = {
        'desktop': [
            os.path.join(home, 'OneDrive', 'Desktop'),
            os.path.join(home, 'Desktop'),
        ],
        'capston': [
            os.path.join(home, 'OneDrive', 'Desktop', 'capston'),
            os.path.join(home, 'Desktop', 'capston'),
        ],
        'capstone': [
            os.path.join(home, 'OneDrive', 'Desktop', 'capston'),
            os.path.join(home, 'Desktop', 'capston'),
        ],
        'downloads': [
            os.path.join(home, 'Downloads'),
            os.path.join(home, 'OneDrive', 'Downloads'),
        ],
        'download': [
            os.path.join(home, 'Downloads'),
            os.path.join(home, 'OneDrive', 'Downloads'),
        ],
        'documents': [
            os.path.join(home, 'OneDrive', 'Documents'),
            os.path.join(home, 'Documents'),
        ],
        'document': [
            os.path.join(home, 'OneDrive', 'Documents'),
            os.path.join(home, 'Documents'),
        ],
    }

    target_dirs = []
    f_clean = folder_name.strip().lower()

    if f_clean in folder_map:
        target_dirs = [d for d in folder_map[f_clean] if os.path.isdir(d)]
    elif f_clean:
        bases = [
            os.path.join(home, 'OneDrive', 'Desktop'),
            os.path.join(home, 'Downloads'),
            os.path.join(home, 'OneDrive', 'Documents'),
            home
        ]
        for b in bases:
            cand = os.path.join(b, folder_name)
            if os.path.isdir(cand):
                target_dirs.append(cand)
            if os.path.isdir(b):
                try:
                    for sub in os.listdir(b):
                        if sub.lower() == f_clean and os.path.isdir(os.path.join(b, sub)):
                            target_dirs.append(os.path.join(b, sub))
                except Exception:
                    pass

    if not target_dirs:
        for key in ['desktop', 'downloads', 'documents']:
            target_dirs.extend([d for d in folder_map[key] if os.path.isdir(d)])

    found = []
    q = query.strip().lower()
    seen_paths = set()

    for base_dir in target_dirs:
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', 'AppData', '__pycache__')]
            for f in files:
                if f.lower().endswith('.pdf'):
                    if not q or (q in f.lower()):
                        full_path = os.path.abspath(os.path.join(root, f))
                        if full_path in seen_paths:
                            continue
                        seen_paths.add(full_path)
                        try:
                            mtime = os.path.getmtime(full_path)
                            size = os.path.getsize(full_path)
                            rel_folder = os.path.basename(os.path.dirname(full_path)) or os.path.basename(base_dir)
                            found.append({
                                'path': full_path,
                                'filename': f,
                                'folder': rel_folder,
                                'mtime': mtime,
                                'size': size
                            })
                        except Exception:
                            pass
            if len(found) >= max_results * 2:
                break

    found.sort(key=lambda x: x['mtime'], reverse=True)
    return found[:max_results]
