import io, os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
import braille, learning, ocr
from app import create_app


@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / 'p.db')).test_client()


# ---------- engine ----------
def test_ascii_letters():
    r = braille.convert_full('abcdefghijklmnopqrstuvwxyz', 'en', 1)
    assert r['ascii'] == 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

def test_capital_and_number():
    assert braille.convert_full('Hello, World 42!', 'en', 1)['ascii'] == ',HELLO1 ,WORLD #DB6'

def test_grade2_contractions():
    assert braille.convert_full('the teaching shop', 'en', 2)['ascii'] == '! TEA*+ %OP'

def test_detect_language():
    assert braille.detect_language('नमस्ते') == 'hi'
    assert braille.detect_language('hello') == 'en'

def test_hindi_basic_and_unicode_range():
    r = braille.convert_full('नमस्ते', 'hi', 1)
    assert r['count'] > 0 and all(0x2800 <= ord(ch) <= 0x283F for ch in r['braille'])

def test_unsupported_reported():
    r = braille.convert_full('a€b', 'en', 1)
    assert '€' in r['unsupported']

def test_ascii_roundtrip():
    cells = braille.convert_full('hello world', 'en', 1)['cells']
    assert braille.from_ascii(braille.to_ascii(cells)) == cells

def test_brf_wraps_at_width():
    cells = braille.convert_full('word ' * 30, 'en', 1)['cells']
    assert all(len(l) <= 40 for l in braille.to_brf(cells, 40).splitlines())


# ---------- learning ----------
def test_learning_persistence(tmp_path):
    p = str(tmp_path / 'l.db')
    s = learning.Store(p)
    item = learning.items_of('en-letters')[0]['id']
    s.record('u', 'en-letters', item, True)
    s2 = learning.Store(p)
    assert s2.summary('u')[0]['attempts'] >= 1 if isinstance(s2.summary('u'), list) else True
    assert s2.mastery('u', 'en-letters') >= 0

def test_leitner_box_moves(tmp_path):
    s = learning.Store(str(tmp_path / 'l.db'))
    item = learning.items_of('en-letters')[0]['id']
    b1 = s.record('u', 'en-letters', item, True)
    b2 = s.record('u', 'en-letters', item, False)
    assert b2 <= b1


# ---------- API ----------
def test_health(client):
    d = client.get('/api/health').get_json()
    assert d['ok'] is True

def test_convert_api(client):
    d = client.post('/api/convert', json={'text': 'abc', 'lang': 'en', 'grade': 1}).get_json()
    assert d['cells'] == [1, 3, 9] and d['ascii'] == 'ABC'

def test_convert_empty(client):
    assert client.post('/api/convert', json={'text': ''}).get_json()['count'] == 0

def test_decode_api(client):
    # 'abc' in Unicode Braille: ⠁⠃⠉
    d = client.post('/api/decode', json={'braille': '⠁⠃⠉', 'lang': 'en'}).get_json()
    assert d['text'] == 'abc'
    d2 = client.post('/api/decode', json={'cells': [1, 3, 9], 'lang': 'en'}).get_json()
    assert d2['text'] == 'abc'

def test_quiz_read_flow(client):
    q = client.get('/api/quiz/next?set=en-letters&mode=read&user=t').get_json()
    assert len(q['options']) == 4 and 'cell' in q
    r = client.post('/api/quiz/answer', json={'user': 't', 'set': 'en-letters', 'mode': 'read', 'item': q['item'], 'choice': q['item']}).get_json()
    assert r['correct'] is True

def test_quiz_write_hides_cell(client):
    q = client.get('/api/quiz/next?set=en-letters&mode=write&user=t').get_json()
    assert 'cell' not in q
    r = client.post('/api/quiz/answer', json={'user': 't', 'set': 'en-letters', 'mode': 'write', 'item': q['item'], 'cell': 0}).get_json()
    assert r['correct'] is False and r['answer_cell'] > 0

def test_unknown_set(client):
    assert client.post('/api/quiz/answer', json={'set': 'nope', 'item': 'x'}).status_code == 400

def test_device_send_without_port(client):
    assert client.post('/api/device/send', json={'port': '', 'cells': [1]}).status_code == 400

def test_virtual_device_send(client):
    r = client.post('/api/device/send', json={'port': 'VIRTUAL', 'cells': [1, 2], 'delay': 0.1})
    assert r.status_code == 200
    st = client.get('/api/device/status').get_json()
    assert st['available'] is True


# ---------- OCR (runs whenever an OCR engine is available) ----------
@pytest.mark.skipif(not ocr.status()['available'], reason='no OCR engine available')
def test_ocr_reads_rendered_text():
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (700, 160), 'white')
    font = None
    for name in ('arial.ttf', 'DejaVuSans.ttf', 'calibri.ttf'):
        try:
            font = ImageFont.truetype(name, 48)
            break
        except OSError:
            pass
    if font is None:
        font = ImageFont.load_default(size=40)
    ImageDraw.Draw(img).text((20, 40), 'Braille Bridge', fill='black', font=font)
    b = io.BytesIO(); img.save(b, 'PNG')
    assert 'braille' in ocr.read_text(b.getvalue(), 'eng').lower()

