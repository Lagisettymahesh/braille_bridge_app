"""Document processing for Braille Bridge: PDF text extraction, OCR fallback, document search,
and independent voice-controlled file browsing and management.
"""
import io
import os
import glob
import re
from typing import Dict, Any, List, Optional
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {
    'pdf': ('.pdf',),
    'text': ('.txt', '.brf', '.rtf', '.md', '.csv'),
    'image': ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
}
ALL_SUPPORTED_EXT = tuple(ext for exts in SUPPORTED_EXTENSIONS.values() for ext in exts)

ORDINAL_MAP = {
    'first': 0, '1st': 0, 'one': 0, '1': 0,
    'second': 1, '2nd': 1, 'two': 1, '2': 1,
    'third': 2, '3rd': 2, 'three': 2, '3': 2,
    'fourth': 3, '4th': 3, 'four': 3, '4': 3,
    'fifth': 4, '5th': 4, 'five': 4, '5': 4,
    'sixth': 5, '6th': 5, 'six': 5, '6': 5,
    'seventh': 6, '7th': 6, 'seven': 6, '7': 6,
    'eighth': 7, '8th': 7, 'eight': 7, '8': 7,
    'ninth': 8, '9th': 8, 'nine': 8, '9': 8,
    'tenth': 9, '10th': 9, 'ten': 9, '10': 9,
}


def get_permitted_roots() -> Dict[str, str]:
    """Retrieve allowed base directories for hands-free voice file management.

    Ensures blind users can access Desktop, Downloads, Documents, Capstone/project folders,
    while strictly disallowing traversal outside authorized user directories.
    """
    home = os.path.expanduser('~')
    roots = {}

    for cand in [os.path.join(home, 'OneDrive', 'Documents'), os.path.join(home, 'Documents')]:
        if os.path.isdir(cand):
            roots['documents'] = os.path.abspath(cand)
            roots['document'] = os.path.abspath(cand)
            break

    for cand in [os.path.join(home, 'Downloads'), os.path.join(home, 'OneDrive', 'Downloads')]:
        if os.path.isdir(cand):
            roots['downloads'] = os.path.abspath(cand)
            roots['download'] = os.path.abspath(cand)
            break

    for cand in [os.path.join(home, 'OneDrive', 'Desktop'), os.path.join(home, 'Desktop')]:
        if os.path.isdir(cand):
            roots['desktop'] = os.path.abspath(cand)
            break

    for cand in [os.path.join(home, 'OneDrive', 'Desktop', 'capston'), os.path.join(home, 'Desktop', 'capston')]:
        if os.path.isdir(cand):
            roots['capston'] = os.path.abspath(cand)
            roots['capstone'] = os.path.abspath(cand)
            break

    cwd = os.path.abspath(os.getcwd())
    if os.path.isdir(cwd):
        roots['workspace'] = cwd
        roots['app'] = cwd

    return roots


def is_path_permitted(target_path: str) -> bool:
    """Ensure target path is strictly within one of the permitted root directories."""
    if not target_path:
        return False
    try:
        norm_target = os.path.realpath(os.path.abspath(target_path))
        win_dir = os.environ.get('WINDIR', 'C:\\Windows')
        if norm_target.lower().startswith(os.path.realpath(win_dir).lower()):
            return False

        roots = get_permitted_roots()
        for root in roots.values():
            norm_root = os.path.realpath(root)
            if norm_target.lower().startswith(norm_root.lower() + os.sep) or norm_target.lower() == norm_root.lower():
                return True
        return False
    except Exception:
        return False


def resolve_permitted_path(folder_alias_or_path: str = 'documents', subpath: str = '') -> Optional[str]:
    """Resolve a folder alias or path securely into an authorized canonical directory."""
    roots = get_permitted_roots()
    alias = str(folder_alias_or_path or '').strip().lower()
    base_dir = roots.get(alias)

    if not base_dir:
        if os.path.isdir(folder_alias_or_path) and is_path_permitted(folder_alias_or_path):
            base_dir = os.path.abspath(folder_alias_or_path)
        else:
            base_dir = roots.get('documents') or roots.get('downloads') or roots.get('desktop')

    if not base_dir or not os.path.isdir(base_dir):
        return None

    if subpath:
        clean_sub = subpath.lstrip('\\/').replace('..', '')
        cand = os.path.abspath(os.path.join(base_dir, clean_sub))
        if is_path_permitted(cand) and os.path.isdir(cand):
            return cand

    return base_dir


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable units."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def resolve_ordinal_selection(phrase: str, total_items: int, filenames: Optional[List[str]] = None) -> Optional[int]:
    """Parse user voice input into a 0-based candidate index.

    Supports:
    - Ordinals: 'first', 'second', 'third', 'fourth', 'fifth', 'last'
    - Numbers: '1', '2', '3', 'one', 'two', 'three'
    - Phrases: 'select the second one', 'select number 2', 'choose the third'
    - Partial filename matching if filenames list is provided.
    """
    if total_items <= 0:
        return None

    phrase_clean = phrase.lower().strip()
    words = phrase_clean.split()
    if 'last' in words or 'last one' in phrase_clean:
        return total_items - 1

    # Check for ordinal words and digits
    tokens = re.findall(r'[a-zA-Z0-9]+', phrase_clean)
    for t in tokens:
        if t in ORDINAL_MAP:
            idx = ORDINAL_MAP[t]
            if 0 <= idx < total_items:
                return idx

    # Check if phrase matches any filename (longest match first)
    if filenames:
        scored = []
        phrase_tokens = set(re.findall(r'[a-zA-Z0-9]+', phrase_clean)) - {'select', 'open', 'choose', 'the', 'file', 'please', 'one'}
        for idx, fn in enumerate(filenames):
            base_fn = os.path.splitext(fn.lower())[0]
            if base_fn and base_fn in phrase_clean:
                scored.append((len(base_fn) * 10, idx))
            elif base_fn:
                fn_tokens = set(re.findall(r'[a-zA-Z0-9]+', base_fn))
                common = fn_tokens.intersection(phrase_tokens)
                if common:
                    scored.append((len(common), idx))
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored[0][1]

    return None



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


def browse_folder(
    folder_alias_or_path: str = 'documents',
    subpath: str = '',
    page: int = 1,
    page_size: int = 8
) -> Dict[str, Any]:
    """Browse a permitted folder or subfolder for documents.

    Returns structured folder metadata, subfolders, paginated files with 1-based IDs,
    and a clear spoken summary designed for blind users navigating via voice.
    """
    resolved = resolve_permitted_path(folder_alias_or_path, subpath)
    if not resolved:
        return {
            'ok': False,
            'error': 'Permission denied: Access to this directory is not permitted.',
            'spoken_summary': 'Access to this folder is not permitted. Please choose Documents, Downloads, or Desktop.'
        }

    folder_display = os.path.basename(resolved) or folder_alias_or_path

    # Check if parent is permitted for "go back" voice navigation
    parent = os.path.dirname(resolved)
    can_go_back = is_path_permitted(parent) and parent != resolved

    subfolders = []
    found_files = []

    try:
        entries = os.listdir(resolved)
    except Exception as e:
        return {
            'ok': False,
            'error': f"Cannot read directory: {e}",
            'spoken_summary': f"Could not open folder {folder_display}."
        }

    for item in entries:
        if item.startswith('.') or item in ('node_modules', '__pycache__', 'AppData'):
            continue
        full = os.path.join(resolved, item)
        if os.path.isdir(full):
            subfolders.append(item)
        elif os.path.isfile(full):
            ext = os.path.splitext(item)[1].lower()
            if ext in ALL_SUPPORTED_EXT:
                try:
                    size = os.path.getsize(full)
                    mtime = os.path.getmtime(full)
                    found_files.append({
                        'filename': item,
                        'name': item,
                        'ext': ext,
                        'path': full,
                        'size': size,
                        'size_str': format_file_size(size),
                        'mtime': mtime,
                        'type': 'pdf' if ext == '.pdf' else ('image' if ext in SUPPORTED_EXTENSIONS['image'] else 'text')
                    })
                except Exception:
                    pass

    found_files.sort(key=lambda x: x['mtime'], reverse=True)
    subfolders.sort(key=str.lower)

    total_files = len(found_files)
    total_pages = max(1, (total_files + page_size - 1) // page_size) if total_files > 0 else 1
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    page_files = found_files[start_idx:start_idx + page_size]

    for i, f in enumerate(page_files):
        f['id'] = i + 1

    if total_files == 0:
        spoken = f"Folder {folder_display} is empty. No document or PDF files were found. You can say open Downloads or open Desktop."
    elif total_files == 1:
        spoken = f"In folder {folder_display}, I found 1 file: Number 1: {page_files[0]['filename']}. Would you like to select it?"
    else:
        file_lines = [f"Number {f['id']}: {f['filename']}" for f in page_files]
        items_str = ". ".join(file_lines)
        more_str = " Say next page to hear more files, or select a file by speaking its name or number." if page < total_pages else " Which one would you like?"
        spoken = f"In folder {folder_display}, I found {total_files} files: {items_str}.{more_str}"

    return {
        'ok': True,
        'folder_name': folder_display,
        'path': resolved,
        'parent_path': parent if can_go_back else None,
        'can_go_back': can_go_back,
        'subfolders': subfolders[:20],
        'files': page_files,
        'total_files': total_files,
        'page': page,
        'total_pages': total_pages,
        'spoken_summary': spoken
    }


def search_files(
    query: str,
    folder_alias: str = '',
    max_results: int = 10
) -> Dict[str, Any]:
    """Search for files matching user query across permitted folders.

    Ranks matches by relevance, numbers them from 1 to N, and formats spoken text
    so blind users can simply say "select the second one" or "number two".
    """
    roots = get_permitted_roots()
    target_dirs = []

    clean_f = folder_alias.strip().lower()
    if clean_f and clean_f in roots:
        target_dirs = [roots[clean_f]]
    else:
        for p in roots.values():
            if p not in target_dirs:
                target_dirs.append(p)

    q_raw = query.strip().lower()
    fillers = {'find', 'my', 'the', 'search', 'for', 'please', 'show', 'open', 'file', 'document', 'a', 'an', 'upload'}
    tokens = [t for t in re.findall(r'[a-zA-Z0-9_\-]+', q_raw) if t not in fillers]

    ext_filter = None
    if 'pdf' in q_raw.split():
        ext_filter = '.pdf'
    elif 'txt' in q_raw.split() or 'text' in q_raw.split():
        ext_filter = ('.txt', '.brf')

    found_files = []
    seen = set()

    for base_dir in target_dirs:
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', 'AppData', '__pycache__')]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext not in ALL_SUPPORTED_EXT:
                    continue
                if ext_filter:
                    if isinstance(ext_filter, tuple) and ext not in ext_filter:
                        continue
                    elif isinstance(ext_filter, str) and ext != ext_filter:
                        continue

                f_lower = f.lower()
                match = False
                score = 0
                if not tokens:
                    match = True
                else:
                    matched_tokens = sum(1 for t in tokens if t in f_lower)
                    if matched_tokens > 0:
                        match = True
                        score = matched_tokens * 10
                        if all(t in f_lower for t in tokens):
                            score += 20
                        if ' '.join(tokens) in f_lower:
                            score += 30

                if match:
                    full = os.path.abspath(os.path.join(root, f))
                    if full in seen:
                        continue
                    seen.add(full)
                    try:
                        mtime = os.path.getmtime(full)
                        size = os.path.getsize(full)
                        folder_name = os.path.basename(os.path.dirname(full))
                        found_files.append({
                            'filename': f,
                            'name': f,
                            'ext': ext,
                            'path': full,
                            'folder': folder_name,
                            'size': size,
                            'size_str': format_file_size(size),
                            'mtime': mtime,
                            'score': score,
                            'type': 'pdf' if ext == '.pdf' else ('image' if ext in SUPPORTED_EXTENSIONS['image'] else 'text')
                        })
                    except Exception:
                        pass
            if len(found_files) >= max_results * 3:
                break

    found_files.sort(key=lambda x: (x['score'], x['mtime']), reverse=True)
    res_files = found_files[:max_results]

    for i, f in enumerate(res_files):
        f['id'] = i + 1

    if not res_files:
        spoken = f"I could not find any files matching '{query}'. Would you like to open your Documents, Downloads, or Desktop folder?"
    elif len(res_files) == 1:
        f = res_files[0]
        spoken = f"I found 1 matching file: Number 1: {f['filename']} in your {f['folder']} folder. Would you like to select it?"
    else:
        file_lines = [f"Number {f['id']}: {f['filename']}" for f in res_files]
        spoken = f"I found {len(res_files)} matching files: {'. '.join(file_lines)}. Which one would you like?"

    return {
        'ok': True,
        'query': query,
        'folder': folder_alias or 'all',
        'found': len(res_files),
        'files': res_files,
        'spoken_summary': spoken
    }


def process_selected_file(
    file_path: str,
    page_range: str = 'all',
    ocr_lang: str = 'eng',
    lang: str = 'auto',
    grade: int = 1
) -> Dict[str, Any]:
    """Process an uploaded or selected document into text and Braille output.

    Handles:
    - Normal text-based PDFs
    - Scanned PDFs via OCR fallback
    - Plain text and BRF files
    - Images via OCR
    - Automatic Braille translation (UEB Grade 1/2, Bharati Braille)
    - Generates spoken completion status for blind users.
    """
    if not is_path_permitted(file_path):
        raise PermissionError(f"Access to file '{file_path}' is not permitted.")
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: '{file_path}'")

    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()

    text = ""
    pages = 1
    total_pages = 1
    is_scanned = False
    method = 'direct'
    warning = None

    if ext == '.pdf':
        with open(file_path, 'rb') as f:
            pdf_bytes = f.read()
        pdf_res = extract_pdf_text(pdf_bytes, page_range=page_range, ocr_lang=ocr_lang)
        text = pdf_res['text']
        pages = pdf_res['pages']
        total_pages = pdf_res['total_pages']
        is_scanned = pdf_res['is_scanned']
        method = pdf_res['method']
        warning = pdf_res['warning']
    elif ext in SUPPORTED_EXTENSIONS['image']:
        try:
            import ocr
            with open(file_path, 'rb') as f:
                img_bytes = f.read()
            text = ocr.read_text(img_bytes, ocr_lang)
            method = 'ocr_image'
        except Exception as e:
            raise RuntimeError(f"OCR failed for {filename}: {e}")
    else:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
                text = f.read()
        method = 'text_file'

    chars = len(text)

    import braille
    conv = {}
    if text:
        conv = braille.convert_full(text[:200000], lang, grade)
        conv['brf'] = braille.to_brf(conv['cells'])

    cell_count = conv.get('count', 0)

    if chars > 0:
        spoken = (
            f"Successfully processed {filename}. "
            f"Extracted {chars} characters across {pages} page{'s' if pages != 1 else ''}, "
            f"converted into {cell_count} Braille cells. "
            f"You can say 'play' to feel each cell or 'read text' to listen."
        )
    else:
        spoken = f"{filename} was opened, but no readable text could be found."

    return {
        'ok': True,
        'filename': filename,
        'path': file_path,
        'ext': ext,
        'folder': os.path.basename(os.path.dirname(file_path)),
        'text': text,
        'chars': chars,
        'pages': pages,
        'total_pages': total_pages,
        'is_scanned': is_scanned,
        'method': method,
        'warning': warning,
        'conversion': conv,
        'spoken_summary': spoken
    }

