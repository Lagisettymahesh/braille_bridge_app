"""Braille Bridge – Local Web Application Backend (Flask).
Provides RESTful APIs for Text-to-Braille conversion, PDF extraction, OCR,
Leitner spaced repetition learning, and ESP32 hardware cell communication.
"""
import os
import logging
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
import braille
import learning
import ocr
import device
import documents

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('braille_bridge')

MAX_TEXT = 200000
MAX_UPLOAD_SIZE = 16 * 1024 * 1024  # 16 MB


def create_app(db_path=None):
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE
    store = learning.Store(db_path)

    def err(msg, code=400):
        return jsonify(ok=False, error=str(msg)), code

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return err(f"Uploaded file exceeds maximum limit of {MAX_UPLOAD_SIZE // (1024 * 1024)} MB.", 413)

    @app.get('/')
    @app.get('/index.html')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.get('/api/health')
    def health():
        return jsonify(
            ok=True,
            service='Braille Bridge API',
            version='2.0.0',
            ocr=ocr.status(),
            serial=device.available()
        )

    # ---------------- Conversion ----------------
    @app.post('/api/convert')
    def convert():
        d = request.get_json(silent=True) or {}
        text = str(d.get('text', ''))
        lang = str(d.get('lang', 'auto')).strip().lower()
        grade_raw = d.get('grade', 1)

        try:
            grade = int(grade_raw)
        except (ValueError, TypeError):
            return err('Grade must be 1 or 2')

        if len(text) > MAX_TEXT:
            return err(f'Text length ({len(text)}) exceeds maximum allowable limit of {MAX_TEXT} characters')
        if lang not in ('auto', 'en', 'hi'):
            return err('Language must be "auto", "en", or "hi"')
        if grade not in (1, 2):
            return err('Grade must be 1 or 2')

        try:
            r = braille.convert_full(text, lang, grade)
            r['brf'] = braille.to_brf(r['cells'])
            r['ok'] = True
            return jsonify(r)
        except Exception as e:
            logger.error(f"Conversion error: {e}", exc_info=True)
            return err(f"Conversion failed: {e}", 500)

    @app.post('/api/decode')
    def decode_braille():
        d = request.get_json(silent=True) or {}
        b_input = str(d.get('braille', ''))
        lang = str(d.get('lang', 'en')).strip().lower()
        if lang not in ('en', 'hi'):
            return err('Language must be "en" or "hi"')

        cells = d.get('cells')
        try:
            if cells and isinstance(cells, list):
                text = braille.decode_cells(cells, lang)
            else:
                text = braille.decode(b_input, lang)
            return jsonify(ok=True, text=text, count=len(text), lang=lang)
        except Exception as e:
            logger.error(f"Decoding error: {e}", exc_info=True)
            return err(f"Decoding failed: {e}", 500)

    # ---------------- Documents & OCR ----------------
    @app.post('/api/ocr')
    def ocr_image():
        f = request.files.get('image')
        if not f:
            return err('Attach an image in the "image" field')
        filename = secure_filename(f.filename or 'upload.png').lower()

        if filename.endswith('.pdf'):
            try:
                res = documents.extract_pdf_text(f.read())
                return jsonify(
                    ok=True,
                    text=res['text'],
                    chars=res['chars'],
                    pages=res['pages'],
                    is_scanned=res['is_scanned'],
                    method=res.get('method', 'digital')
                )
            except Exception as e:
                return err(f'PDF extraction error: {e}')

        try:
            ocr_lang = request.form.get('ocr_lang', 'eng')
            text = ocr.read_text(f.read(), ocr_lang)
            return jsonify(ok=True, text=text, chars=len(text), lang=ocr_lang)
        except ValueError as e:
            return err(str(e))
        except RuntimeError as e:
            return err(str(e), 503)
        except Exception as e:
            return err(f"OCR processing failed: {e}", 500)

    @app.post('/api/upload-pdf')
    def upload_pdf():
        f = request.files.get('pdf') or request.files.get('file') or request.files.get('document')
        if not f:
            return err('Attach a PDF document in the "pdf" or "file" field')

        filename = secure_filename(f.filename or 'document.pdf')
        if not filename.lower().endswith('.pdf'):
            return err('The uploaded file must be a .pdf document')

        try:
            data = f.read()
            if not data.startswith(b'%PDF-'):
                return err('Invalid PDF: file header does not match PDF signature (%PDF-).')

            page_range = request.form.get('page_range', 'all')
            ocr_lang = request.form.get('ocr_lang', 'eng')
            res = documents.extract_pdf_text(data, page_range=page_range, ocr_lang=ocr_lang)
        except ValueError as e:
            return err(str(e))
        except Exception as e:
            logger.error(f"PDF extraction error: {e}", exc_info=True)
            return err(f"Failed to process PDF: {e}", 500)

        auto_convert = request.form.get('convert', 'false').lower() in ('1', 'true', 'yes')
        lang = request.form.get('lang', 'auto')
        grade_raw = request.form.get('grade', 1)
        try:
            grade = int(grade_raw)
        except Exception:
            grade = 1

        payload = {
            'ok': True,
            'filename': filename,
            'text': res['text'],
            'pages': res['pages'],
            'total_pages': res['total_pages'],
            'chars': res['chars'],
            'is_scanned': res['is_scanned'],
            'method': res.get('method', 'digital'),
            'warning': res.get('warning'),
            'pages_detail': res.get('pages_detail', [])
        }

        if auto_convert and res['text']:
            try:
                c_res = braille.convert_full(res['text'][:MAX_TEXT], lang, grade)
                c_res['brf'] = braille.to_brf(c_res['cells'])
                payload['conversion'] = c_res
            except Exception as e:
                logger.warning(f"Auto-convert error: {e}")

        return jsonify(payload)

    @app.route('/api/find-local-pdf', methods=['GET', 'POST'])
    def find_local_pdf():
        if request.method == 'POST':
            d = request.get_json(silent=True) or request.form or {}
        else:
            d = request.args or {}

        folder = str(d.get('folder', ''))
        query = str(d.get('query', ''))
        path = str(d.get('path', ''))
        auto_load = str(d.get('load', '1')).lower() in ('1', 'true', 'yes')
        lang = str(d.get('lang', 'auto'))
        grade = int(d.get('grade', 1)) if str(d.get('grade', 1)).isdigit() else 1
        page_range = str(d.get('page_range', 'all'))

        if path and os.path.isfile(path) and path.lower().endswith('.pdf'):
            files = [{'path': path, 'filename': os.path.basename(path), 'folder': os.path.basename(os.path.dirname(path))}]
        else:
            files = documents.find_local_pdfs(folder, query)

        if not files:
            msg = f"No PDF files found{' in folder ' + folder if folder else ''}{' matching ' + query if query else ''}."
            return jsonify(ok=False, message=msg, found=0, files=[])

        payload = {
            'ok': True,
            'found': len(files),
            'files': files,
            'folder': folder or 'system',
            'query': query
        }

        if auto_load and files:
            target_file = files[0]
            try:
                with open(target_file['path'], 'rb') as f_obj:
                    content = f_obj.read()
                res = documents.extract_pdf_text(content, page_range=page_range)
                conv = {}
                if res['text']:
                    conv = braille.convert_full(res['text'][:MAX_TEXT], lang, grade)
                    conv['brf'] = braille.to_brf(conv['cells'])
                payload['loaded'] = {
                    'filename': target_file['filename'],
                    'path': target_file['path'],
                    'folder': target_file['folder'],
                    'text': res['text'],
                    'chars': res['chars'],
                    'pages': res['pages'],
                    'total_pages': res.get('total_pages', res['pages']),
                    'is_scanned': res['is_scanned'],
                    'conversion': conv,
                    'warning': res.get('warning')
                }
            except Exception as e:
                payload['load_error'] = str(e)

        return jsonify(payload)

    # ---------------- Learning Module ----------------
    def uname():
        u = (request.args.get('user') or (request.get_json(silent=True) or {}).get('user') or 'guest').strip()[:40]
        return u or 'guest'

    @app.get('/api/sets')
    def sets():
        return jsonify(store.summary(uname()))

    @app.get('/api/quiz/next')
    def quiz_next():
        sid = request.args.get('set', 'en-beginner')
        mode = request.args.get('mode', 'read')
        rev = request.args.get('revision', 'false').lower() in ('1', 'true', 'yes')

        if sid not in learning.SETS or mode not in ('read', 'write'):
            return err('Unknown set or mode')

        user = uname()
        try:
            item = store.next_item(user, sid, request.args.get('last'), revision_only=rev)
        except Exception:
            item = store.next_item(user, sid, request.args.get('last'), revision_only=False)

        out = dict(
            ok=True,
            item=item['id'],
            label=item['label'],
            lang=item['lang'],
            mode=mode,
            mastery=store.mastery(user, sid),
            box=store.boxes(user, sid).get(item['id'], 0),
            is_revision=rev
        )

        if mode == 'read':
            import random
            pool = [it for it in learning.items_of(sid) if it['id'] != item['id']]
            opts = random.sample(pool, min(3, len(pool))) + [item]
            random.shuffle(opts)
            out.update(cell=item['cell'], options=[dict(id=o['id'], label=o['label']) for o in opts])

        return jsonify(out)

    @app.post('/api/quiz/answer')
    def quiz_answer():
        d = request.get_json(silent=True) or {}
        sid, mode, item = d.get('set'), d.get('mode', 'read'), d.get('item')
        if sid not in learning.SETS:
            return err('Unknown set')

        target = next((it for it in learning.items_of(sid) if it['id'] == item), None)
        if not target:
            return err('Unknown item')

        if mode == 'read':
            ok = d.get('choice') == item
        else:
            try:
                ok = int(d.get('cell')) == target['cell']
            except (TypeError, ValueError):
                return err('Cell must be an integer 0-63')

        user = uname()
        box = store.record(user, sid, item, ok)
        return jsonify(
            ok=True,
            correct=ok,
            answer_cell=target['cell'],
            answer_label=target['label'],
            box=box,
            mastery=store.mastery(user, sid)
        )

    @app.get('/api/learning/stats')
    def learning_stats():
        return jsonify(store.stats(uname()))

    @app.post('/api/progress/reset')
    def progress_reset():
        store.reset(uname())
        return jsonify(ok=True)

    # ---------------- Hardware & Virtual Simulator ----------------
    @app.get('/api/device/ports')
    def dev_ports():
        return jsonify(available=device.available(), ports=device.ports())

    @app.post('/api/device/send')
    def dev_send():
        d = request.get_json(silent=True) or {}
        try:
            device.send(d.get('port'), d.get('cells', []), float(d.get('delay', 1.0)))
        except (ValueError, TypeError) as e:
            return err(str(e))
        except RuntimeError as e:
            return err(str(e), 409)
        return jsonify(ok=True, started=True)

    @app.get('/api/device/status')
    def dev_status():
        return jsonify(device.status())

    @app.post('/api/device/stop')
    def dev_stop():
        device.stop()
        return jsonify(ok=True)

    @app.post('/api/device/test')
    def dev_test():
        d = request.get_json(silent=True) or {}
        port = d.get('port', device.VIRTUAL_PORT)
        try:
            res = device.test_hardware(port)
            return jsonify(res)
        except Exception as e:
            return err(str(e))

    @app.post('/api/device/ping')
    def dev_ping():
        d = request.get_json(silent=True) or {}
        port = d.get('port', device.VIRTUAL_PORT)
        try:
            res = device.ping(port)
            return jsonify(res)
        except Exception as e:
            return err(str(e))

    return app


app = create_app()

if __name__ == '__main__':
    host = os.environ.get('BRIDGE_HOST', '127.0.0.1')
    port = int(os.environ.get('BRIDGE_PORT', '5050'))
    logger.info(f"Starting Braille Bridge server on http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
