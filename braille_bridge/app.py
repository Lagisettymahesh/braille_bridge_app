"""Braille Bridge – local web application.  Run:  python app.py   then open http://127.0.0.1:5050"""
import os
from flask import Flask, jsonify, request, send_from_directory
import braille, learning, ocr, device

MAX_TEXT = 20000

def create_app(db_path=None):
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
    store = learning.Store(db_path)

    def err(msg, code=400):
        return jsonify(error=msg), code

    @app.get('/')
    @app.get('/index.html')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.get('/api/health')
    def health():
        return jsonify(ok=True, ocr=ocr.status(), serial=device.available())

    # ---------------- conversion ----------------
    @app.post('/api/convert')
    def convert():
        d = request.get_json(silent=True) or {}
        text = str(d.get('text', ''))
        lang, grade = d.get('lang', 'auto'), d.get('grade', 1)
        if len(text) > MAX_TEXT:
            return err(f'Text is too long (limit {MAX_TEXT} characters)')
        if lang not in ('auto', 'en', 'hi') or grade not in (1, 2, '1', '2'):
            return err('lang must be auto/en/hi and grade 1 or 2')
        r = braille.convert_full(text, lang, int(grade))
        r['brf'] = braille.to_brf(r['cells'])
        return jsonify(r)

    @app.post('/api/decode')
    def decode_braille():
        d = request.get_json(silent=True) or {}
        b_input = str(d.get('braille', ''))
        lang = d.get('lang', 'en')
        if lang not in ('en', 'hi'):
            return err('lang must be en or hi')
        cells = d.get('cells')
        if cells and isinstance(cells, list):
            text = braille.decode_cells(cells, lang)
        else:
            text = braille.decode(b_input, lang)
        return jsonify(text=text, count=len(text), lang=lang)

    @app.post('/api/ocr')
    def ocr_image():
        f = request.files.get('image')
        if not f:
            return err('Attach an image in the "image" field')
        try:
            text = ocr.read_text(f.read(), request.form.get('ocr_lang', 'eng'))
        except ValueError as e:
            return err(str(e))
        except RuntimeError as e:
            return err(str(e), 503)
        return jsonify(text=text, chars=len(text))

    # ---------------- learning ----------------
    def uname():
        u = (request.args.get('user') or (request.get_json(silent=True) or {}).get('user') or 'guest').strip()[:40]
        return u or 'guest'

    @app.get('/api/sets')
    def sets():
        return jsonify(store.summary(uname()))

    @app.get('/api/quiz/next')
    def quiz_next():
        sid, mode = request.args.get('set', 'en-letters'), request.args.get('mode', 'read')
        if sid not in learning.SETS or mode not in ('read', 'write'):
            return err('unknown set or mode')
        user = uname()
        item = store.next_item(user, sid, request.args.get('last'))
        out = dict(item=item['id'], label=item['label'], lang=item['lang'], mode=mode,
                   mastery=store.mastery(user, sid), box=store.boxes(user, sid).get(item['id'], 0))
        if mode == 'read':                      # show the cell, choose the character
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
            return err('unknown set')
        target = next((it for it in learning.items_of(sid) if it['id'] == item), None)
        if not target:
            return err('unknown item')
        if mode == 'read':
            ok = d.get('choice') == item
        else:
            try:
                ok = int(d.get('cell')) == target['cell']
            except (TypeError, ValueError):
                return err('cell must be an integer 0-63')
        user = uname()
        box = store.record(user, sid, item, ok)
        return jsonify(correct=ok, answer_cell=target['cell'], answer_label=target['label'], box=box,
                       mastery=store.mastery(user, sid))

    @app.post('/api/progress/reset')
    def progress_reset():
        store.reset(uname())
        return jsonify(ok=True)

    # ---------------- hardware ----------------
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
        return jsonify(started=True)

    @app.get('/api/device/status')
    def dev_status():
        return jsonify(device.status())

    @app.post('/api/device/stop')
    def dev_stop():
        device.stop()
        return jsonify(ok=True)

    return app

app = create_app()

if __name__ == '__main__':
    host = os.environ.get('BRIDGE_HOST', '127.0.0.1')
    app.run(host=host, port=int(os.environ.get('BRIDGE_PORT', '5050')), debug=False)
