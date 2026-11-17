"""Comprehensive automated test suite for Braille Bridge:
Covers Braille translation engine (UEB Grade 1 & 2, Bharati Hindi Braille),
PDF processing, OCR, Leitner learning system, REST API, hardware simulation,
security, and performance benchmarks.
"""
import io
import os
import sys
import shutil
import time
import pytest
from pypdf import PdfWriter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import braille
import learning
import ocr
import device
import documents
from app import create_app


@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / 'test_progress.db')).test_client()


# ==============================================================================
# 1. BRAILLE TRANSLATION ENGINE: ENGLISH UEB GRADE 1 & 2
# ==============================================================================
def test_ascii_letters():
    r = braille.convert_full('abcdefghijklmnopqrstuvwxyz', 'en', 1)
    assert r['ascii'] == 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    assert len(r['cells']) == 26


def test_capital_and_number():
    r = braille.convert_full('Hello, World 42!', 'en', 1)
    # UEB: ',' indicates capital letter; '#DB' indicates digits 4, 2
    assert r['ascii'] == ',HELLO1 ,WORLD #DB6'


def test_all_digits():
    r = braille.convert_full('0123456789', 'en', 1)
    assert r['ascii'] == '#JABCDEFGHI'


def test_numbers_with_decimal_and_comma():
    # In UEB: '.' after number uses dot 46 (ASCII '4'), comma uses dot 2 (ASCII '1')
    r1 = braille.convert_full('3.14', 'en', 1)
    assert r1['ascii'] == '#C4AD'
    r2 = braille.convert_full('1,000', 'en', 1)
    assert r2['ascii'] == '#A1JJJ'


def test_multi_word_all_caps():
    # Double capital indicator ',,' for capitalized word
    r = braille.convert_full('NASA', 'en', 1)
    assert r['ascii'] == ',,NASA'


def test_grade2_contractions():
    # UEB Grade 2: 'the' -> '!', 'ch' -> '*', 'ing' -> '+', 'sh' -> '%'
    assert braille.convert_full('the teaching shop', 'en', 2)['ascii'] == '! TEA*+ %OP'


def test_grade2_standalone_wordsigns():
    # UEB Grade 2 single-letter whole wordsigns: but -> b, can -> c, you -> y, it -> x
    r = braille.convert_full('you can do it but not that', 'en', 2)
    assert r['ascii'] == 'Y C D X B N T'


def test_grade2_strong_words():
    # Strong words: and (&), for (=), of (( paren ), the (!), with ())
    r = braille.convert_full('and for of the with', 'en', 2)
    assert r['ascii'] == '& = ( ! )'


def test_grade2_groupsigns():
    # Test common UEB group signs within words
    r = braille.convert_full('child stand water worker ghost', 'en', 2)
    assert '*' in r['ascii']  # ch
    assert '/' in r['ascii']  # st
    assert ']' in r['ascii']  # er
    assert '<' in r['ascii']  # gh


def test_special_symbols():
    # Check UEB special symbols
    symbols = '@ & % / + = < > * $'
    r = braille.convert_full(symbols, 'en', 1)
    assert r['count'] > 0
    assert len(r['unsupported']) == 0


def test_brackets_and_quotes():
    r = braille.convert_full('(hello) [world]', 'en', 1)
    assert r['count'] > 0
    assert len(r['unsupported']) == 0


def test_empty_string():
    r = braille.convert_full('', 'en', 1)
    assert r['cells'] == []
    assert r['ascii'] == ''
    assert r['braille'] == ''
    assert r['count'] == 0


def test_unsupported_characters():
    r = braille.convert_full('hello € world §', 'en', 1)
    assert '€' in r['unsupported']
    assert '§' in r['unsupported']


def test_ascii_roundtrip():
    cells = braille.convert_full('quick brown fox 123', 'en', 1)['cells']
    ascii_str = braille.to_ascii(cells)
    decoded_cells = braille.from_ascii(ascii_str)
    assert decoded_cells == cells


def test_brf_wrapping_and_formatting():
    text = "Line one\nLine two\n" + ("longword " * 20)
    cells = braille.convert_full(text, 'en', 1)['cells']
    brf = braille.to_brf(cells, width=40)
    lines = brf.splitlines()
    assert all(len(line) <= 40 for line in lines)
    assert len(lines) >= 2


# ==============================================================================
# 2. BHARATI BRAILLE ENGINE: HINDI
# ==============================================================================
def test_detect_language():
    assert braille.detect_language('नमस्ते भारत') == 'hi'
    assert braille.detect_language('Hello World') == 'en'
    assert braille.detect_language('12345') == 'en'


def test_hindi_basic_vowels():
    # Check that Hindi vowels map cleanly to standard 6-dot cells
    r = braille.convert_full('अ आ इ ई उ ऊ ऋ ए ऐ ओ औ', 'hi', 1)
    assert r['count'] > 0
    assert all(0x2800 <= ord(ch) <= 0x283F for ch in r['braille'])


def test_hindi_basic_consonants():
    # Check that Hindi consonants map without error
    r = braille.convert_full('क ख ग घ च छ ज झ ट ठ ड ढ त थ द ध न प फ ब भ म', 'hi', 1)
    assert r['count'] > 0
    assert len(r['unsupported']) == 0


def test_hindi_conjuncts():
    # Bharati Braille single-cell conjuncts: क्ष, ज्ञ, त्र, श्र
    r = braille.convert_full('क्षत्रिय ज्ञान आश्रम', 'hi', 1)
    assert r['count'] > 0
    assert len(r['unsupported']) == 0


def test_hindi_matras_and_halant():
    r = braille.convert_full('किताब और सूर्य', 'hi', 1)
    assert r['count'] > 0
    assert all(0x2800 <= ord(ch) <= 0x283F for ch in r['braille'])


def test_hindi_marks_anusvara_visarga():
    r = braille.convert_full('संसार स्वतः', 'hi', 1)
    assert r['count'] > 0
    assert len(r['unsupported']) == 0


def test_mixed_hindi_english():
    # System should auto-switch or handle tokens gracefully
    r = braille.convert_full('Hello दुनिया 100', 'auto', 1)
    assert r['count'] > 0
    assert all(0x2800 <= ord(ch) <= 0x283F for ch in r['braille'])


def test_bidirectional_cell_decoding():
    # Decode cells back to text
    cells = braille.convert_full('bridge', 'en', 1)['cells']
    text = braille.decode_cells(cells, 'en')
    assert text.lower() == 'bridge'


def test_unicode_braille_decode():
    # 'abc' in Unicode Braille: ⠁⠃⠉
    decoded = braille.decode('⠁⠃⠉', 'en')
    assert decoded.lower() == 'abc'


# ==============================================================================
# 3. PDF PROCESSING & OCR
# ==============================================================================
def test_parse_page_range():
    assert documents.parse_page_range('all', 10) == list(range(10))
    assert documents.parse_page_range('', 5) == list(range(5))
    assert documents.parse_page_range('1-3', 10) == [0, 1, 2]
    assert documents.parse_page_range('2, 4', 5) == [1, 3]
    assert documents.parse_page_range('1-2, 5', 10) == [0, 1, 4]
    assert documents.parse_page_range('invalid', 3) == [0, 1, 2]


def test_pdf_extraction_multi_page():
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    w.add_blank_page(width=72, height=72)
    w.add_blank_page(width=72, height=72)
    b = io.BytesIO()
    w.write(b)

    # All pages
    res_all = documents.extract_pdf_text(b.getvalue(), page_range='all')
    assert res_all['pages'] == 3
    assert res_all['total_pages'] == 3

    # Selected pages 1-2
    res_part = documents.extract_pdf_text(b.getvalue(), page_range='1-2')
    assert res_part['pages'] == 2
    assert res_part['total_pages'] == 3


def test_pdf_corrupt_data():
    with pytest.raises(ValueError, match="Invalid PDF format"):
        documents.extract_pdf_text(b'not a real pdf file')


def test_find_local_pdfs_in_temp(tmp_path):
    sub = tmp_path / 'my_docs'
    sub.mkdir()
    pdf_file = sub / 'report.pdf'
    w = PdfWriter()
    w.add_blank_page(width=50, height=50)
    with open(pdf_file, 'wb') as f:
        w.write(f)

    results = documents.find_local_pdfs(str(sub))
    assert len(results) >= 1
    assert any(r['filename'] == 'report.pdf' for r in results)


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
    b = io.BytesIO()
    img.save(b, 'PNG')
    assert 'braille' in ocr.read_text(b.getvalue(), 'eng').lower()


# ==============================================================================
# 4. BRAILLE LEARNING MODULE (LEITNER SPACED REPETITION)
# ==============================================================================
def test_learning_tiered_sets():
    assert 'en-beginner' in learning.SETS
    assert 'en-intermediate' in learning.SETS
    assert 'en-advanced' in learning.SETS
    assert 'hi-beginner' in learning.SETS
    assert 'hi-intermediate' in learning.SETS
    assert 'hi-advanced' in learning.SETS


def test_learning_persistence(tmp_path):
    p = str(tmp_path / 'learn.db')
    s = learning.Store(p)
    s.record('testuser', 'en-beginner', 'a', True)
    s2 = learning.Store(p)
    summary = s2.summary('testuser')
    beg = next(item for item in summary if item['id'] == 'en-beginner')
    assert beg['attempts'] == 1
    assert beg['correct'] == 1


def test_leitner_box_movement(tmp_path):
    s = learning.Store(str(tmp_path / 'boxes.db'))
    # Correct moves box from 0 -> 1 -> 2
    b1 = s.record('u', 'en-beginner', 'b', True)
    assert b1 == 1
    b2 = s.record('u', 'en-beginner', 'b', True)
    assert b2 == 2
    # Miss demotes immediately to 0
    b3 = s.record('u', 'en-beginner', 'b', False)
    assert b3 == 0


def test_learning_daily_stats(tmp_path):
    s = learning.Store(str(tmp_path / 'stats.db'))
    s.record('u', 'en-beginner', 'c', True)
    s.record('u', 'en-beginner', 'd', False)
    stats = s.stats('u')
    assert stats['total_attempts'] == 2
    assert stats['total_correct'] == 1
    assert stats['accuracy'] == 50.0
    assert len(stats['daily_history']) >= 1


def test_learning_revision_count_and_mode(tmp_path):
    s = learning.Store(str(tmp_path / 'rev.db'))
    # Wrong answer creates a revision requirement
    s.record('u', 'en-beginner', 'z', False)
    assert s.revision_count('u', 'en-beginner') >= 1
    rev_item = s.next_item('u', 'en-beginner', revision_only=True)
    assert rev_item['id'] == 'z'


def test_learning_reset(tmp_path):
    s = learning.Store(str(tmp_path / 'reset.db'))
    s.record('u', 'en-beginner', 'a', True)
    s.reset('u')
    assert s.stats('u')['total_attempts'] == 0


# ==============================================================================
# 5. HARDWARE CONTROLLER & SIMULATOR
# ==============================================================================
def test_device_ports_listing():
    p = device.ports()
    assert len(p) >= 1
    assert any(x['device'] == 'VIRTUAL' for x in p)


def test_device_ping_virtual():
    res = device.ping('VIRTUAL')
    assert res['ok'] is True
    assert res['port'] == 'VIRTUAL'


def test_device_virtual_stream():
    device.stop()
    time.sleep(0.1)
    device.send('VIRTUAL', [1, 3], delay=0.02)
    time.sleep(0.1)
    st = device.status()
    assert st['available'] is True


def test_device_hardware_test_virtual():
    device.stop()
    time.sleep(0.15)
    res = device.test_hardware('VIRTUAL', delay=0.02)
    assert res['ok'] is True
    assert res['started'] is True
    time.sleep(0.2)
    device.stop()


def test_device_stop():
    device.stop()
    st = device.status()
    assert 'running' in st
    assert st['available'] is True


# ==============================================================================
# 6. REST API ENDPOINTS & VALIDATION
# ==============================================================================
def test_api_health(client):
    d = client.get('/api/health').get_json()
    assert d['ok'] is True
    assert d['version'] == '2.0.0'


def test_api_convert_success(client):
    d = client.post('/api/convert', json={'text': 'hello', 'lang': 'en', 'grade': 1}).get_json()
    assert d['ok'] is True
    assert d['ascii'] == 'HELLO'
    assert len(d['cells']) == 5


def test_api_convert_auto_language(client):
    d = client.post('/api/convert', json={'text': 'नमस्ते', 'lang': 'auto'}).get_json()
    assert d['ok'] is True
    assert d['lang'] == 'hi'


def test_api_convert_grade2(client):
    d = client.post('/api/convert', json={'text': 'the people', 'lang': 'en', 'grade': 2}).get_json()
    assert d['ok'] is True
    assert d['ascii'] == '! P'


def test_api_convert_validation_invalid_grade(client):
    r = client.post('/api/convert', json={'text': 'test', 'grade': 5})
    assert r.status_code == 400


def test_api_convert_validation_invalid_language(client):
    r = client.post('/api/convert', json={'text': 'test', 'lang': 'french'})
    assert r.status_code == 400


def test_api_decode_cells(client):
    r = client.post('/api/decode', json={'cells': [1, 3, 9], 'lang': 'en'}).get_json()
    assert r['ok'] is True
    assert r['text'].lower() == 'abc'


def test_api_upload_pdf_valid(client):
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    b = io.BytesIO()
    w.write(b)
    b.seek(0)
    data = {'pdf': (b, 'doc.pdf')}
    r = client.post('/api/upload-pdf', data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    res = r.get_json()
    assert res['ok'] is True
    assert res['filename'] == 'doc.pdf'
    assert res['pages'] == 1


def test_api_upload_pdf_invalid_signature(client):
    data = {'pdf': (io.BytesIO(b'not a pdf header'), 'fake.pdf')}
    r = client.post('/api/upload-pdf', data=data, content_type='multipart/form-data')
    assert r.status_code == 400
    assert 'signature' in r.get_json()['error'].lower()


def test_api_upload_pdf_page_range(client):
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    w.add_blank_page(width=72, height=72)
    b = io.BytesIO()
    w.write(b)
    b.seek(0)
    data = {'pdf': (b, 'two_pages.pdf'), 'page_range': '1'}
    r = client.post('/api/upload-pdf', data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    assert r.get_json()['pages'] == 1


def test_api_learning_summary_and_stats(client):
    sets_res = client.get('/api/sets?user=testuser').get_json()
    assert len(sets_res) >= 6
    stats_res = client.get('/api/learning/stats?user=testuser').get_json()
    assert 'accuracy' in stats_res


def test_api_quiz_next_and_answer(client):
    q = client.get('/api/quiz/next?set=en-beginner&mode=read&user=u').get_json()
    assert q['ok'] is True
    assert len(q['options']) == 4
    ans = client.post('/api/quiz/answer', json={
        'user': 'u', 'set': 'en-beginner', 'mode': 'read',
        'item': q['item'], 'choice': q['item']
    }).get_json()
    assert ans['ok'] is True
    assert ans['correct'] is True


def test_api_device_test_and_stop(client):
    r_test = client.post('/api/device/test', json={'port': 'VIRTUAL'}).get_json()
    assert r_test['ok'] is True
    r_stop = client.post('/api/device/stop').get_json()
    assert r_stop['ok'] is True


def test_api_device_ping(client):
    r = client.post('/api/device/ping', json={'port': 'VIRTUAL'}).get_json()
    assert r['ok'] is True


# ==============================================================================
# 7. PERFORMANCE & LOAD BENCHMARK
# ==============================================================================
def test_performance_conversion_benchmark():
    # 5,000 character sample
    text = "Unified English Braille translation benchmark test string with numbers 12345. " * 65
    assert len(text) >= 5000
    t0 = time.perf_counter()
    res = braille.convert_full(text, 'en', 2)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert res['count'] > 0
    # Must complete in under 100ms
    assert elapsed_ms < 100.0, f"Conversion took {elapsed_ms:.2f} ms (expected < 100 ms)"
