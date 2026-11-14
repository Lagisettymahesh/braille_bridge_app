"""OCR front-end: light pre-processing + Tesseract or Windows Media OCR (English / Hindi)."""
import io, os, shutil, sys, tempfile, subprocess
from PIL import Image, ImageOps, ImageFilter

MAX_SIDE = 4000
_cached_status = None

def _find_tesseract():
    exe = shutil.which('tesseract')
    if exe:
        return exe
    candidates = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe'),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

def _check_windows_ocr():
    if sys.platform != 'win32':
        return False, []
    try:
        ps = (
            "[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null; "
            "[Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages | "
            "ForEach-Object { $_.LanguageTag }"
        )
        res = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps],
                             capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            tags = [t.strip().lower() for t in res.stdout.splitlines() if t.strip()]
            langs = []
            if any(t.startswith('en') for t in tags):
                langs.append('eng')
            if any(t.startswith('hi') for t in tags):
                langs.append('hin')
            if not langs and tags:
                langs = ['eng']
            return True, langs
    except Exception:
        pass
    return False, []

def status():
    global _cached_status
    if _cached_status is not None:
        return _cached_status

    # 1. Try Tesseract
    tess_exe = _find_tesseract()
    if tess_exe:
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tess_exe
            langs = [l for l in pytesseract.get_languages(config='') if l != 'osd']
            _cached_status = {'available': True, 'languages': langs, 'engine': 'tesseract'}
            return _cached_status
        except Exception:
            pass

    # 2. Try Windows native OCR
    win_ok, win_langs = _check_windows_ocr()
    if win_ok:
        _cached_status = {'available': True, 'languages': win_langs, 'engine': 'windows_media_ocr'}
        return _cached_status

    _cached_status = {
        'available': False,
        'languages': [],
        'hint': 'Install Tesseract OCR (with eng/hin language data) or enable Windows OCR language packs.'
    }
    return _cached_status

def preprocess(img):
    img = ImageOps.exif_transpose(img).convert('L')
    if max(img.size) > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE))
    if img.width < 1200:                         # small photos: enlarge so characters are at least ~30 px high
        k = 1200 / img.width
        img = img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
    img = ImageOps.autocontrast(img, cutoff=1)
    return img.filter(ImageFilter.SHARPEN)

def _windows_ocr_recognize(img):
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name
        img.save(tmp, format='PNG')
    try:
        ps_script = f'''
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }})[0]
function Await($winRtTask, $resultType) {{
    $asTask = $asTaskGeneric.MakeGenericMethod($resultType)
    $netTask = $asTask.Invoke($null, @($winRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}}
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync('{tmp_path}')) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$softwareBitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$ocrResult = Await ($engine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult])
Write-Output $ocrResult.Text
'''
        res = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps_script],
                             capture_output=True, text=True, check=True, timeout=15)
        return '\n'.join(line.rstrip() for line in res.stdout.splitlines()).strip()
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

def read_text(data, lang='eng'):
    if lang not in ('eng', 'hin', 'eng+hin'):
        raise ValueError('lang must be eng, hin or eng+hin')
    st = status()
    if not st['available']:
        raise RuntimeError(st.get('hint', 'OCR is not available'))

    try:
        img = Image.open(io.BytesIO(data)); img.load()
    except Exception:
        raise ValueError('The file is not a readable image')

    pre = preprocess(img)

    if st.get('engine') == 'tesseract':
        for part in lang.split('+'):
            if part not in st['languages']:
                raise RuntimeError(f'Tesseract language data "{part}" is not installed')
        import pytesseract
        text = pytesseract.image_to_string(pre, lang=lang, config='--psm 6')
        return '\n'.join(line.rstrip() for line in text.splitlines()).strip()
    elif st.get('engine') == 'windows_media_ocr':
        if lang == 'hin' and 'hin' not in st['languages']:
            raise RuntimeError('Hindi OCR requires Tesseract with Hindi data or Windows Hindi language pack.')
        return _windows_ocr_recognize(pre)
    else:
        raise RuntimeError('No OCR engine available')
