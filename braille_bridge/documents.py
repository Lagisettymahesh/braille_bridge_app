"""Document processing for Braille Bridge: PDF text extraction and document helpers."""
import io
import os
import glob
from typing import Dict, Any, List
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
        # Check subdirectories of common bases
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
            # Case-insensitive match on directory names
            if os.path.isdir(b):
                try:
                    for sub in os.listdir(b):
                        if sub.lower() == f_clean and os.path.isdir(os.path.join(b, sub)):
                            target_dirs.append(os.path.join(b, sub))
                except Exception:
                    pass

    if not target_dirs:
        # Default to searching Desktop, Downloads, and Documents
        for key in ['desktop', 'downloads', 'documents']:
            target_dirs.extend([d for d in folder_map[key] if os.path.isdir(d)])

    found = []
    q = query.strip().lower()
    seen_paths = set()

    for base_dir in target_dirs:
        for root, dirs, files in os.walk(base_dir):
            # Avoid node_modules, .git, AppData, etc.
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

    # Sort newest files first
    found.sort(key=lambda x: x['mtime'], reverse=True)
    return found[:max_results]
