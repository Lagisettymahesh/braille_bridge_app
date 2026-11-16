'use strict';
const $ = s => document.querySelector(s);
const DOTPOS = [[20, 18], [20, 45], [20, 72], [40, 18], [40, 45], [40, 72]];
const state = { result: null, idx: 0, timer: null, quiz: null, answered: false, editCell: 0, testCell: 0 };

/* ---------- helpers ---------- */
function setStatus(msg, kind) { const s = $('#status'); s.textContent = msg || ''; s.className = 'status ' + (kind || ''); }
async function api(path, opts) {
  let r;
  try { r = await fetch(path, opts); } catch (e) { throw new Error('Cannot reach the Braille Bridge server'); }
  let data = {}; try { data = await r.json(); } catch (e) {}
  if (!r.ok) throw new Error(data.error || ('Request failed (' + r.status + ')'));
  return data;
}
const post = (p, body) => api(p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
function dotsOf(c) { const d = []; for (let i = 0; i < 6; i++) if (c >> i & 1) d.push(i + 1); return d; }
function describe(c) { const d = dotsOf(c); return d.length ? 'dots ' + d.join('-') : 'blank cell'; }

function cellSVG(code, px, opts = {}) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 60 90'); svg.setAttribute('width', px); svg.setAttribute('height', px * 1.5);
  svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', 'Braille cell, ' + describe(code));
  DOTPOS.forEach(([x, y], i) => {
    const g = document.createElementNS(ns, 'g'); g.dataset.dot = i + 1;
    const c = document.createElementNS(ns, 'circle'); c.setAttribute('cx', x); c.setAttribute('cy', y); c.setAttribute('r', 8);
    c.setAttribute('class', 'd' + ((code >> i & 1) ? ' on' : '')); g.appendChild(c);
    if (opts.numbers) {
      const t = document.createElementNS(ns, 'text'); t.setAttribute('x', x); t.setAttribute('y', y + 3.5); t.setAttribute('text-anchor', 'middle');
      t.setAttribute('font-size', '10'); t.setAttribute('fill', (code >> i & 1) ? 'var(--brand-ink)' : 'var(--muted)'); t.textContent = i + 1; g.appendChild(t);
    }
    svg.appendChild(g);
  });
  return svg;
}
function speak(text, lang, onDone) {
  if (!('speechSynthesis' in window) || !text) {
    if (onDone) onDone();
    return;
  }
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang || 'en-IN';
  state.isSpeaking = true;
  u.onend = () => {
    state.isSpeaking = false;
    if (onDone) onDone();
  };
  u.onerror = () => {
    state.isSpeaking = false;
    if (onDone) onDone();
  };
  speechSynthesis.speak(u);
}
function download(name, text, type) {
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; a.click(); URL.revokeObjectURL(a.href);
}
function el(tag, props = {}, ...kids) { const e = Object.assign(document.createElement(tag), props); kids.forEach(k => e.append(k)); return e; }

/* ---------- tabs ---------- */
const TABS = ['convert', 'learn', 'device'];
function showTab(name) {
  TABS.forEach(t => {
    const sel = t === name; $('#t-' + t).setAttribute('aria-selected', sel); $('#t-' + t).tabIndex = sel ? 0 : -1; $('#p-' + t).hidden = !sel;
  });
  if (name === 'learn') { refreshSets(); if (!state.quiz) nextQuestion(); }
  if (name === 'device') refreshPorts();
  setStatus('');
}
TABS.forEach((t, i) => {
  $('#t-' + t).addEventListener('click', () => showTab(t));
  $('#t-' + t).addEventListener('keydown', e => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      const n = TABS[(i + (e.key === 'ArrowRight' ? 1 : TABS.length - 1)) % TABS.length]; showTab(n); $('#t-' + n).focus();
    }
  });
});

/* ---------- convert ---------- */
function applyConversionResult(r, note) {
  state.result = r; state.idx = 0; stopPlay();
  $('#unicode').textContent = r.braille; $('#unicode').lang = 'en';
  $('#meta').textContent = `${r.count} cells · ${r.lang === 'hi' ? 'Hindi (Bharati Braille)' : 'English Grade ' + r.grade} ${note || ''}`;
  const w = $('#warn'); w.hidden = !r.unsupported || !r.unsupported.length;
  if (r.unsupported && r.unsupported.length) {
    w.textContent = 'These characters are not supported yet and were shown as a full cell: ' + r.unsupported.join(' ');
  }
  ['#btn-copy', '#btn-brf', '#btn-txt', '#btn-speak'].forEach(b => $(b).disabled = false);
  const strip = $('#strip'); strip.replaceChildren();
  const maxStripCells = Math.min(r.cells.length, 300);
  for (let i = 0; i < maxStripCells; i++) {
    const c = r.cells[i];
    const b = el('button', { className: 'cellbox', type: 'button', title: 'Cell ' + (i + 1) + ': ' + describe(c) });
    b.append(cellSVG(c, 26), el('small', {}, c ? r.ascii[i] : '␣'));
    b.addEventListener('click', () => { stopPlay(); showCell(i); });
    strip.append(b);
  }
  if (r.cells.length > maxStripCells) {
    strip.append(el('p', { className: 'hint', style: 'width:100%; text-align:center; margin:0.4rem 0;' },
      `Showing first ${maxStripCells} of ${r.cells.length} cells. Use the Player below or Download .brf for full output.`));
  }
  showCell(0);
}

async function convert() {
  const text = $('#text').value;
  if (!text.trim()) { setStatus('Enter some text first.', 'bad'); return; }
  try {
    const r = await post('/api/convert', { text, lang: $('#lang').value, grade: +$('#grade').value });
    applyConversionResult(r);
    setStatus('Converted ' + r.count + ' cells.', 'ok');
  } catch (e) { setStatus(e.message, 'bad'); }
}
$('#btn-convert').onclick = convert;
$('#text').addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) convert(); });
$('#btn-clear').onclick = () => { $('#text').value = ''; $('#text').focus(); };
$('#btn-sample').onclick = () => {
  $('#text').value = $('#lang').value === 'hi' ? 'नमस्ते, मैं ब्रेल सीख रहा हूँ।' : 'The quick brown fox jumps over the lazy dog. Room 42!';
  convert();
};
$('#btn-copy').onclick = async () => {
  try { await navigator.clipboard.writeText(state.result.braille); setStatus('Braille copied.', 'ok'); } catch (e) { setStatus('Copy is blocked by the browser; select the text instead.', 'bad'); }
};
$('#btn-brf').onclick = () => download('braille.brf', state.result.brf, 'text/plain');
$('#btn-txt').onclick = () => download('braille.txt', state.result.braille, 'text/plain;charset=utf-8');
$('#btn-speak').onclick = () => speak($('#text').value, state.result.lang === 'hi' ? 'hi-IN' : 'en-IN');

/* ---------- PDF and Document Upload ---------- */
async function handlePdfUpload(f) {
  if (!f) return;
  showTab('convert');
  setStatus('Reading and extracting PDF: ' + f.name + '…');
  const fd = new FormData();
  fd.append('pdf', f);
  fd.append('convert', '1');
  fd.append('lang', $('#lang').value);
  fd.append('grade', $('#grade').value);
  try {
    const r = await api('/api/upload-pdf', { method: 'POST', body: fd });
    if (!r.text && r.is_scanned) {
      const w = `Scanned PDF detected (${r.pages} page(s)). No digital text could be extracted.`;
      setStatus(w, 'bad');
      speak('Scanned PDF detected with no digital text.');
      return;
    }
    $('#text').value = r.text || '';
    if (r.conversion && r.conversion.cells) {
      applyConversionResult(r.conversion, `from "${r.filename}"`);
      const msg = `PDF "${r.filename}" loaded: ${r.chars} characters converted to ${r.conversion.count} Braille cells.`;
      setStatus(msg, 'ok');
      speak(`PDF loaded. Converted normal text to Braille text successfully. Generated ${r.conversion.count} Braille cells.`);
    } else {
      await convert();
      speak(`PDF loaded. Converted normal text to Braille text successfully.`);
    }
  } catch (err) {
    setStatus(err.message, 'bad');
    speak('Error processing PDF: ' + err.message);
  }
}
if ($('#pdf-file')) {
  $('#pdf-file').addEventListener('change', e => {
    handlePdfUpload(e.target.files[0]);
    e.target.value = '';
  });
}
if ($('#btn-quick-pdf')) {
  $('#btn-quick-pdf').onclick = () => $('#pdf-file').click();
}

/* Quick folder scan buttons */
if ($('#btn-quick-desktop')) $('#btn-quick-desktop').onclick = () => searchAndLoadLocalPdf('desktop');
if ($('#btn-quick-downloads')) $('#btn-quick-downloads').onclick = () => searchAndLoadLocalPdf('downloads');
if ($('#btn-quick-documents')) $('#btn-quick-documents').onclick = () => searchAndLoadLocalPdf('documents');

async function searchAndLoadLocalPdf(folder, query) {
  showTab('convert');
  const folderDesc = folder ? `folder "${folder}"` : 'your folders';
  setStatus(`Scanning ${folderDesc} for PDF…`);
  const transcriptEl = $('#va-transcript');
  if (transcriptEl) transcriptEl.innerHTML = `Scanning <strong>${folder || 'system folders'}</strong> for PDF…`;

  try {
    const url = `/api/find-local-pdf?folder=${encodeURIComponent(folder || '')}&query=${encodeURIComponent(query || '')}&load=1&lang=${encodeURIComponent($('#lang').value)}&grade=${encodeURIComponent($('#grade').value)}`;
    const r = await api(url);

    if (!r.ok || !r.found) {
      const failMsg = `No PDF found in ${folderDesc}. Opening file selector so you can choose it manually.`;
      setStatus(failMsg, 'bad');
      speak(failMsg, 'en-IN', () => {
        setTimeout(() => { if ($('#pdf-file')) $('#pdf-file').click(); }, 300);
      });
      return;
    }

    if (r.loaded) {
      const item = r.loaded;
      $('#text').value = item.text || '';
      if (item.conversion && item.conversion.cells) {
        state.result = item.conversion;
        state.idx = 0;
        stopPlay();
        $('#unicode').textContent = item.conversion.braille;
        $('#meta').textContent = `${item.conversion.count} cells · Extracted from "${item.filename}" (${item.folder})`;
        ['#btn-copy', '#btn-brf', '#btn-txt', '#btn-speak'].forEach(b => $(b).disabled = false);
        const strip = $('#strip'); strip.replaceChildren();
        item.conversion.cells.forEach((c, i) => {
          const b = el('button', { className: 'cellbox', type: 'button', title: 'Cell ' + (i + 1) + ': ' + describe(c) });
          b.append(cellSVG(c, 26), el('small', {}, c ? item.conversion.ascii[i] : '␣'));
          b.addEventListener('click', () => { stopPlay(); showCell(i); });
          strip.append(b);
        });
        showCell(0);
      } else if (item.text) {
        await convert();
      }

      const msg = `Found and loaded "${item.filename}" from ${item.folder} (${item.chars} chars across ${item.pages} page(s)).`;
      setStatus(msg, 'ok');
      speak(`Found and loaded ${item.filename} from your ${item.folder} folder. Converted to Braille successfully.`);

      if (transcriptEl) {
        transcriptEl.innerHTML = `Loaded: "<strong>${item.filename}</strong>" from <em>${item.folder}</em>`;
      }
      renderFoundPdfChips(r.files);
    }
  } catch (err) {
    setStatus(`Error searching folder: ${err.message}`, 'bad');
    speak(`Error finding PDF: ${err.message}`);
  }
}

function renderFoundPdfChips(files) {
  if (!files || files.length <= 1) return;
  let container = $('#va-found-files');
  if (!container) {
    container = el('div', { id: 'va-found-files', style: 'margin-top:0.6rem; display:flex; flex-wrap:wrap; gap:0.35rem; align-items:center;' });
    const banner = $('#va-banner');
    if (banner) banner.querySelector('.va-chips').parentNode.appendChild(container);
  }
  container.replaceChildren(el('span', { style: 'font-size:0.8rem; font-weight:600; color:var(--muted);' }, 'Other PDFs in folder: '));
  files.slice(1, 6).forEach(f => {
    const chip = el('button', {
      type: 'button',
      className: 'va-chip',
      style: 'border-color:var(--brand); font-size:0.78rem;',
      title: f.path
    }, '📄 ' + f.filename);
    chip.onclick = () => loadDirectPdfPath(f.path, f.filename);
    container.append(chip);
  });
}

async function loadDirectPdfPath(path, filename) {
  setStatus(`Loading ${filename}…`);
  try {
    const r = await api(`/api/find-local-pdf?path=${encodeURIComponent(path)}&load=1&lang=${encodeURIComponent($('#lang').value)}&grade=${encodeURIComponent($('#grade').value)}`);
    if (r.loaded) {
      $('#text').value = r.loaded.text || '';
      await convert();
      speak(`Loaded ${filename} and converted to Braille.`);
    }
  } catch(e) {
    setStatus(e.message, 'bad');
  }
}

/* ---------- OCR ---------- */
$('#file').addEventListener('change', async e => {
  const f = e.target.files[0]; if (!f) return;
  if (f.name.toLowerCase().endsWith('.pdf') || f.type === 'application/pdf') {
    handlePdfUpload(f);
    e.target.value = '';
    return;
  }
  setStatus('Reading the page…');
  const fd = new FormData(); fd.append('image', f); fd.append('ocr_lang', $('#ocr-lang').value);
  try {
    const r = await api('/api/ocr', { method: 'POST', body: fd });
    $('#text').value = r.text;
    if ($('#ocr-lang').value === 'hin') $('#lang').value = 'hi';
    setStatus(r.chars ? `Recognised ${r.chars} characters. Please check the text before using the Braille.` : 'No text was found in the image.', r.chars ? 'ok' : 'bad');
    if (r.chars) await convert();
  } catch (err) { setStatus(err.message, 'bad'); }
  e.target.value = '';
});

/* ---------- Voice Assistant ---------- */
(function () {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const btnToggle = $('#btn-va-toggle');
  const banner = $('#va-banner');
  const bannerClose = $('#va-close');
  const statusText = $('#va-status-text');
  const transcriptEl = $('#va-transcript');
  if (!btnToggle) return;

  let vaActive = false;
  let recognition = null;
  let restartTimer = null;
  let isListening = false;

  function announce(msg, callback) {
    if (transcriptEl) transcriptEl.innerHTML = `<strong>${msg}</strong>`;
    // Pause recognition while speaking to prevent acoustic self-triggering
    pauseListening();
    speak(msg, $('#lang').value === 'hi' ? 'hi-IN' : 'en-IN', () => {
      resumeListening();
      if (callback) callback();
    });
  }

  function pauseListening() {
    if (recognition && isListening) {
      try { recognition.abort(); } catch (e) {}
      isListening = false;
    }
  }

  function resumeListening() {
    if (vaActive && !isListening && !state.isSpeaking) {
      clearTimeout(restartTimer);
      restartTimer = setTimeout(() => {
        if (vaActive && !state.isSpeaking) startListening();
      }, 350);
    }
  }

  function setVAState(active, speakGreeting = true) {
    vaActive = active;
    btnToggle.classList.toggle('active', active);
    btnToggle.setAttribute('aria-pressed', String(active));
    if (banner) banner.hidden = !active;
    if (active) {
      if (statusText) statusText.textContent = 'Voice Assistant Active';
      if (speakGreeting) {
        const greeting = getGreeting();
        const msg = `${greeting} Welcome to Braille Bridge. What file do you want to upload, and what file do you want to convert?`;
        announce(msg, () => {
          if (statusText) statusText.textContent = 'Opening file selector now…';
          setTimeout(() => {
            if ($('#pdf-file')) $('#pdf-file').click();
          }, 400);
        });
      } else {
        startListening();
      }
    } else {
      stopListening();
      setStatus('');
    }
  }

  function startListening() {
    if (!SR) {
      setStatus('Speech recognition is not supported in this browser. Please use Chrome or Edge.', 'bad');
      return;
    }
    if (state.isSpeaking) return;
    if (recognition && isListening) return;

    try {
      recognition = new SR();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = $('#lang').value === 'hi' ? 'hi-IN' : 'en-US';

      recognition.onstart = () => {
        isListening = true;
        if (statusText) statusText.textContent = 'Listening for commands…';
      };

      recognition.onresult = event => {
        // If system is currently speaking, discard any detected echo
        if (state.isSpeaking) return;

        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            const phrase = event.results[i][0].transcript.trim().toLowerCase();
            processCommand(phrase);
          }
        }
      };

      recognition.onerror = e => {
        if (e.error === 'no-speech') return;
        if (e.error === 'not-allowed') {
          setStatus('Microphone access denied. Please click the camera/mic icon in the address bar to allow.', 'bad');
          setVAState(false);
          return;
        }
        isListening = false;
      };

      recognition.onend = () => {
        isListening = false;
        if (vaActive && !state.isSpeaking) {
          clearTimeout(restartTimer);
          restartTimer = setTimeout(() => {
            if (vaActive && !state.isSpeaking) startListening();
          }, 300);
        }
      };

      recognition.start();
    } catch (err) {
      isListening = false;
    }
  }

  function stopListening() {
    clearTimeout(restartTimer);
    if (recognition) {
      try { recognition.abort(); } catch (e) {}
      recognition = null;
    }
    isListening = false;
  }

  function processCommand(phrase) {
    if (!phrase) return;
    if (transcriptEl) transcriptEl.innerHTML = `Heard: "<strong>${phrase}</strong>"`;

    // 1. Upload PDF
    // Handles: "upload a pdf", "upload apdf", "upload pdf", "upload the pdf", "upload pdf from desktop", etc.
    const isPdfUploadIntent = phrase.includes('pdf') || phrase.includes('document') || phrase.includes('upload file');
    const isUploadAction = phrase.includes('upload') || phrase.includes('load') || phrase.includes('choose') || phrase.includes('select') || phrase.includes('open');

    if (isPdfUploadIntent && isUploadAction) {
      showTab('convert');
      let targetFolder = '';
      let targetQuery = '';

      if (phrase.includes('desktop')) targetFolder = 'desktop';
      else if (phrase.includes('download')) targetFolder = 'downloads';
      else if (phrase.includes('document')) targetFolder = 'documents';
      else if (phrase.includes('capston') || phrase.includes('capstone')) targetFolder = 'capston';

      if (phrase.includes('report')) targetQuery = 'report';
      else if (phrase.includes('assignment')) targetQuery = 'assignment';
      else if (phrase.includes('mahesh')) targetQuery = 'mahesh';
      else if (phrase.includes('photo')) targetQuery = 'photo';

      if (targetFolder || targetQuery) {
        announce(`Searching for PDF in ${targetFolder || 'your computer'}…`, () => {
          searchAndLoadLocalPdf(targetFolder, targetQuery);
        });
      } else {
        announce('Please choose your PDF file. I will load and convert it to Braille.', () => {
          setTimeout(() => {
            if ($('#pdf-file')) $('#pdf-file').click();
          }, 300);
        });
      }
      return;
    }

    // 2. Open Website / Home
    if (phrase.includes('open website') || phrase.includes('website') || phrase.includes('open home') ||
        phrase.includes('go home') || phrase.includes('home page') || phrase.includes('open convert') ||
        phrase.includes('braille bridge') || phrase.includes('main page')) {
      showTab('convert');
      announce('Showing Braille Bridge home and converter.');
      return;
    }

    // 3. Learn Tab
    if (phrase.includes('open learn') || phrase.includes('learn') || phrase.includes('quiz') || phrase.includes('practice') || phrase.includes('study')) {
      showTab('learn');
      announce('Opening Braille Learning Center.');
      return;
    }

    // 4. Device Tab
    if (phrase.includes('open device') || phrase.includes('device') || phrase.includes('hardware') || phrase.includes('simulator')) {
      showTab('device');
      announce('Opening Hardware Device and Tactile Simulator.');
      return;
    }

    // 5. Convert Normal Text to Braille Text
    if (phrase.includes('convert') || phrase.includes('translate') || phrase.includes('to braille') || phrase.includes('make braille')) {
      showTab('convert');
      if (!$('#text').value.trim()) {
        announce('Please enter text or upload a PDF first.');
      } else {
        announce('Converting normal text to Braille text.', () => {
          convert();
        });
      }
      return;
    }

    // 6. Read Aloud
    if (phrase === 'yes' || phrase === 'sure' || phrase === 'yeah' || phrase.includes('yes read') ||
        phrase.includes('read aloud') || phrase.includes('read text') || phrase.includes('read braille') ||
        phrase.includes('speak') || phrase.includes('read this') || phrase.includes('read it')) {
      const text = $('#text').value;
      if (!text.trim()) {
        announce('No text to read aloud. Please upload a PDF or enter text first.');
      } else {
        announce('Reading text aloud: ' + text);
      }
      return;
    }

    // 7. Clear
    if (phrase.includes('clear') || phrase.includes('reset') || phrase.includes('erase')) {
      $('#text').value = '';
      announce('Text cleared.');
      return;
    }

    // 8. Help
    if (phrase.includes('help') || phrase.includes('command') || phrase.includes('what can you do') || phrase.includes('options')) {
      announce('You can say: Upload PDF, Open website, Convert, Read aloud, Open learn, Open device, or Clear.');
      return;
    }

    // 9. Dictate / Type explicitly
    if (phrase.startsWith('type ') || phrase.startsWith('write ') || phrase.startsWith('dictate ')) {
      const dictatedText = phrase.replace(/^(type|write|dictate)\s+/, '').trim();
      if (dictatedText) {
        $('#text').value += (($('#text').value ? ' ' : '') + dictatedText);
        if (transcriptEl) transcriptEl.innerHTML = `Typed: "<em>${dictatedText}</em>"`;
        announce('Added text: ' + dictatedText);
      }
      return;
    }

    // If unhandled, prompt help without polluting textarea
    if (transcriptEl) {
      transcriptEl.innerHTML = `Heard: "<em>${phrase}</em>" &nbsp;·&nbsp; <small style="color:var(--muted)">Say <strong>"Help"</strong> or click a command below</small>`;
    }
  }

  btnToggle.onclick = () => setVAState(!vaActive);
  if (bannerClose) bannerClose.onclick = () => setVAState(false);

  window.addEventListener('keydown', e => {
    if (e.altKey && (e.key === 'v' || e.key === 'V')) {
      e.preventDefault();
      setVAState(!vaActive);
    }
  });

  document.querySelectorAll('.va-chip').forEach(chip => {
    chip.onclick = () => {
      const cmd = chip.dataset.cmd;
      if (cmd) processCommand(cmd);
    };
  });

  function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return 'Hello and good morning!';
    if (hour < 17) return 'Hello and good afternoon!';
    return 'Hello and good evening!';
  }

  let autoWelcomeDone = false;

  function autoWelcomeAndAsk() {
    if (autoWelcomeDone) return;
    autoWelcomeDone = true;

    vaActive = true;
    btnToggle.classList.add('active');
    btnToggle.setAttribute('aria-pressed', 'true');
    if (banner) banner.hidden = false;

    const greeting = getGreeting();
    const promptMessage = `${greeting} Welcome to Braille Bridge. What file do you want to upload, and what file do you want to convert?`;

    if (statusText) statusText.textContent = 'Voice Assistant Active (Automated)';
    if (transcriptEl) transcriptEl.innerHTML = `<strong>${promptMessage}</strong>`;

    speak(promptMessage, 'en-IN', () => {
      if (statusText) statusText.textContent = 'Opening file selector to upload…';
      setTimeout(() => {
        try {
          if ($('#pdf-file')) $('#pdf-file').click();
        } catch(e) {}
        startListening();
      }, 400);
    });
  }

  // Automatically start as soon as website opens
  setTimeout(autoWelcomeAndAsk, 600);

  // Fallback for browsers with strict gesture policy: any touch, click or keypress unlocks audio & file picker
  function handleFirstUserTouch() {
    if (!autoWelcomeDone) autoWelcomeAndAsk();
    window.removeEventListener('click', handleFirstUserTouch);
    window.removeEventListener('keydown', handleFirstUserTouch);
    window.removeEventListener('touchstart', handleFirstUserTouch);
    window.removeEventListener('pointerdown', handleFirstUserTouch);
  }
  window.addEventListener('click', handleFirstUserTouch);
  window.addEventListener('keydown', handleFirstUserTouch);
  window.addEventListener('touchstart', handleFirstUserTouch);
  window.addEventListener('pointerdown', handleFirstUserTouch);
})();

/* ---------- dictation ---------- */
(function () {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const btn = $('#btn-mic'), note = $('#mic-note');
  if (!SR) { btn.disabled = true; note.textContent = 'Dictation needs Chrome or Edge.'; return; }
  let rec = null;
  btn.onclick = () => {
    if (rec) { rec.stop(); return; }
    rec = new SR(); rec.lang = $('#lang').value === 'hi' ? 'hi-IN' : 'en-IN'; rec.interimResults = false; rec.continuous = true;
    rec.onresult = ev => { for (let i = ev.resultIndex; i < ev.results.length; i++) if (ev.results[i].isFinal) $('#text').value += (($('#text').value && ' ') + ev.results[i][0].transcript.trim()); };
    rec.onend = () => { rec = null; btn.textContent = 'Start dictation'; note.textContent = ''; };
    rec.onerror = e => setStatus('Dictation error: ' + e.error, 'bad');
    rec.start(); btn.textContent = 'Stop dictation'; note.textContent = 'Listening… (' + rec.lang + ')';
  };
})();

/* ---------- player ---------- */
function showCell(i) {
  const r = state.result; if (!r) return;
  state.idx = Math.max(0, Math.min(i, r.cells.length - 1));
  const c = r.cells[state.idx];
  $('#bigcell').replaceChildren(cellSVG(c, 110, { numbers: true }));
  $('#cur').textContent = `Cell ${state.idx + 1} of ${r.cells.length} · ${describe(c)}`;
  document.querySelectorAll('#strip .cellbox').forEach((b, k) => b.classList.toggle('on', k === state.idx));
  const on = document.querySelector('#strip .cellbox.on'); if (on) on.scrollIntoView({ block: 'nearest' });
  if ($('#to-device')?.checked) {
    updateSimulator(c);
  }
}
function stopPlay() { if (state.timer) { clearInterval(state.timer); state.timer = null; } $('#p-play').textContent = 'Play'; }
$('#p-play').onclick = async () => {
  const r = state.result; if (!r) { setStatus('Convert some text first.', 'bad'); return; }
  if (state.timer) { stopPlay(); if ($('#to-device').checked) post('/api/device/stop', {}).catch(() => {}); return; }
  if (state.idx >= r.cells.length - 1) showCell(0);
  const sec = +$('#speed').value;
  if ($('#to-device').checked) {
    try { await post('/api/device/send', { port: $('#port').value, cells: r.cells.slice(state.idx), delay: sec }); }
    catch (e) { setStatus(e.message, 'bad'); }
  }
  $('#p-play').textContent = 'Pause';
  state.timer = setInterval(() => { if (state.idx >= r.cells.length - 1) stopPlay(); else showCell(state.idx + 1); }, sec * 1000);
};
$('#p-next').onclick = () => { stopPlay(); showCell(state.idx + 1); };
$('#p-prev').onclick = () => { stopPlay(); showCell(state.idx - 1); };

/* ---------- learn ---------- */
const mode = () => document.querySelector('input[name=mode]:checked').value;
const user = () => ($('#user').value.trim() || 'guest');
async function refreshSets() {
  try {
    const sets = await api('/api/sets?user=' + encodeURIComponent(user()));
    const sel = $('#set'), cur = sel.value;
    sel.replaceChildren(...sets.map(s => el('option', { value: s.id }, `${s.title} (${Math.round(s.mastery * 100)}%)`)));
    if (cur) sel.value = cur;
    const s = sets.find(x => x.id === sel.value) || sets[0];
    $('#meter-bar').style.width = Math.round(s.mastery * 100) + '%';
    $('#meter-txt').textContent = `Mastered ${Math.round(s.mastery * s.items)} of ${s.items} characters.`;
    $('#prog').replaceChildren(...sets.map(x => el('tr', {}, el('td', {}, x.title), el('td', {}, Math.round(x.mastery * 100) + '%'),
      el('td', {}, String(x.attempts)), el('td', {}, x.attempts ? Math.round(100 * x.correct / x.attempts) + '%' : '—'))));
  } catch (e) { setStatus(e.message, 'bad'); }
}
async function nextQuestion() {
  const q = $('#quiz'); state.answered = false; state.editCell = 0;
  try {
    const d = await api(`/api/quiz/next?user=${encodeURIComponent(user())}&set=${$('#set').value || 'en-letters'}&mode=${mode()}` +
      (state.quiz ? '&last=' + encodeURIComponent(state.quiz.item) : ''));
    state.quiz = d; q.replaceChildren();
    const fb = el('p', { className: 'feedback', id: 'fb' });
    if (d.mode === 'read') {
      q.append(el('h2', {}, 'Which character is this cell?'), el('div', { className: 'big', id: 'qcell' }));
      $('#qcell').append(cellSVG(d.cell, 110, { numbers: true }));
      const o = el('div', { className: 'opts' });
      d.options.forEach(op => { const b = el('button', { type: 'button', lang: d.lang === 'hi-IN' ? 'hi' : 'en' }, op.label); b.dataset.id = op.id; b.onclick = () => answer({ choice: op.id }, b); o.append(b); });
      q.append(o, fb);
    } else {
      q.append(el('h2', {}, 'Set the dots for this character'), el('div', { className: 'glyph', lang: d.lang === 'hi-IN' ? 'hi' : 'en' }, d.label));
      const ed = el('div', { className: 'editor', id: 'qedit' }); q.append(ed); drawEditor(ed, 'editCell');
      q.append(el('p', { className: 'hint' }, 'Click the dots or press keys 1–6, then Enter to check.'),
        el('div', { className: 'actions', style: 'justify-content:center' }, Object.assign(el('button', { className: 'primary', type: 'button' }, 'Check'), { onclick: () => answer({ cell: state.editCell }) })), fb);
      if ($('#speak-on').checked) speak(d.label, d.lang);
    }
    refreshSets();
  } catch (e) { q.replaceChildren(el('p', { className: 'feedback bad' }, e.message)); }
}
function drawEditor(host, key, big = 110) {
  host.replaceChildren(); const svg = cellSVG(state[key], big, { numbers: true }); svg.style.width = big + 'px'; svg.style.height = big * 1.5 + 'px';
  svg.addEventListener('click', ev => { const g = ev.target.closest('g[data-dot]'); if (g) toggleDot(+g.dataset.dot, key, host, big); });
  host.append(svg);
}
function toggleDot(n, key, host, big) {
  state[key] ^= 1 << (n - 1);
  drawEditor(host, key, big);
  if (key === 'testCell') {
    $('#test-code').textContent = 'Cell value ' + state.testCell + ' · ' + describe(state.testCell);
    updateSimulator(state.testCell);
  }
}
async function answer(payload, btn) {
  if (state.answered) return; state.answered = true;
  const d = state.quiz;
  try {
    const r = await post('/api/quiz/answer', Object.assign({ user: user(), set: $('#set').value, mode: d.mode, item: d.item }, payload));
    const fb = $('#fb');
    fb.textContent = r.correct ? 'Correct!' : 'Not quite. The answer is ' + (d.mode === 'read' ? r.answer_label + '.' : describe(r.answer_cell) + '.');
    fb.className = 'feedback ' + (r.correct ? 'ok' : 'bad');
    if (d.mode === 'read') {
      document.querySelectorAll('.opts button').forEach(b => { b.disabled = true; if (b.dataset.id === d.item) b.classList.add('right'); });
      if (btn && !r.correct) btn.classList.add('wrong');
    } else if (!r.correct) {
      $('#qedit').append(cellSVG(r.answer_cell, 70, { numbers: true }));
    }
    if ($('#speak-on').checked && d.mode === 'read') speak(r.answer_label, d.lang);
    $('#quiz').append(el('div', { className: 'actions', style: 'justify-content:center' },
      Object.assign(el('button', { className: 'primary', type: 'button', id: 'btn-next-q' }, 'Next'), { onclick: nextQuestion }),
      Object.assign(el('button', { type: 'button' }, 'Feel it on the Braille cell'), { onclick: () => sendOne(r.answer_cell) })));
    $('#btn-next-q').focus();
    refreshSets();
  } catch (e) { setStatus(e.message, 'bad'); state.answered = false; }
}
async function sendOne(cell) {
  try { await post('/api/device/send', { port: $('#port').value, cells: [cell], delay: 0.5 }); setStatus('Sent to the Braille cell.', 'ok'); }
  catch (e) { setStatus(e.message, 'bad'); }
}
$('#set').onchange = () => { state.quiz = null; nextQuestion(); };
$('#user').onchange = () => { state.quiz = null; refreshSets(); nextQuestion(); };
document.querySelectorAll('input[name=mode]').forEach(r => r.onchange = () => { state.quiz = null; nextQuestion(); });
$('#btn-reset').onclick = async () => { if (confirm('Delete all saved progress for "' + user() + '"?')) { await post('/api/progress/reset', { user: user() }); state.quiz = null; refreshSets(); nextQuestion(); } };
document.addEventListener('keydown', e => {
  if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && document.activeElement.type !== 'radio') return;
  const n = parseInt(e.key, 10);
  if (n >= 1 && n <= 6) {
    if (!$('#p-device').hidden) toggleDot(n, 'testCell', $('#test-cell'), 110);
    else if (!$('#p-learn').hidden && state.quiz && state.quiz.mode === 'write' && !state.answered) toggleDot(n, 'editCell', $('#qedit'), 110);
  } else if (e.key === 'Enter' && !$('#p-learn').hidden && state.quiz && state.quiz.mode === 'write' && !state.answered && document.activeElement.tagName !== 'BUTTON') {
    answer({ cell: state.editCell });
  }
});

/* ---------- device & hardware simulator ---------- */
let audioCtx = null;
function playBuzzer() {
  const chk = $('#sound-on');
  if (chk && !chk.checked) return;
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'square';
    osc.frequency.setValueAtTime(1000, audioCtx.currentTime); // 1000 Hz ESP32 buzzer
    gain.gain.setValueAtTime(0.06, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.06);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.06);
    const led = $('#led-buzzer');
    if (led) { led.classList.add('active'); setTimeout(() => led.classList.remove('active'), 90); }
  } catch (e) {}
}

function flashSerialLed() {
  const led = $('#led-tx');
  if (led) { led.classList.add('active'); setTimeout(() => led.classList.remove('active'), 120); }
}

function initSimulatorChannels() {
  const grid = $('#channels-grid');
  if (!grid) return;
  grid.replaceChildren();
  for (let d = 0; d < 6; d++) {
    const row = el('div', { className: 'channel-row', id: 'ch-row-' + d },
      el('span', {}, `CH${d} (Dot ${d + 1}):`),
      el('div', { className: 'channel-bar' }, el('div', { className: 'channel-fill', id: 'ch-fill-' + d })),
      el('span', { className: 'channel-val', id: 'ch-val-' + d }, '20°')
    );
    grid.append(row);
  }
}

function updateSimulator(code) {
  flashSerialLed();
  playBuzzer();
  const desc = describe(code);
  const meta = $('#sim-cell-meta');
  if (meta) meta.textContent = `Active Cell: ${code} (${desc || 'blank'})`;

  // Staggered actuation (40ms per dot, matching firmware showCell loop)
  for (let d = 0; d < 6; d++) {
    setTimeout(() => {
      const up = (code >> d) & 1;
      const deg = up ? 70 : 20;
      const pin = $(`#tactile-grid .tactile-pin[data-dot="${d + 1}"]`);
      if (pin) {
        pin.classList.toggle('up', !!up);
        const ang = pin.querySelector('.pin-angle');
        if (ang) ang.textContent = deg + '°';
      }
      const row = $(`#ch-row-${d}`);
      if (row) row.classList.toggle('up', !!up);
      const val = $(`#ch-val-${d}`);
      if (val) val.textContent = deg + '°';
    }, d * 40);
  }
}

function setTestDots(code) {
  state.testCell = code;
  drawEditor($('#test-cell'), 'testCell');
  $('#test-code').textContent = 'Cell value ' + code + ' · ' + describe(code);
  updateSimulator(code);
}

async function refreshPorts() {
  try {
    const d = await api('/api/device/ports'); const sel = $('#port');
    sel.replaceChildren(...(d.ports.length ? d.ports.map(p => el('option', { value: p.device }, `${p.device} – ${p.description}`)) : [el('option', { value: '' }, 'No serial ports found')]));
    $('#dev-note').textContent = d.serial_installed ? '' : 'pyserial is not installed on the server (pip install pyserial). The Virtual Simulator works completely.';
  } catch (e) { setStatus(e.message, 'bad'); }
}
$('#btn-ports').onclick = refreshPorts;

let poll = null;
let lastSimCell = -1;
function watch() {
  clearInterval(poll);
  poll = setInterval(async () => {
    try {
      const s = await api('/api/device/status');
      $('#dev-bar').style.width = s.total ? Math.round(100 * s.sent / s.total) + '%' : '0%';
      $('#dev-status').textContent = s.error ? 'Error: ' + s.error : s.running ? `Sending ${s.sent} of ${s.total}…` : (s.total ? `Done: ${s.sent} of ${s.total} cells sent.` : 'Idle.');
      if (s.running && s.current_cell !== undefined && s.current_cell !== lastSimCell) {
        lastSimCell = s.current_cell;
        updateSimulator(s.current_cell);
      }
      if (!s.running) {
        clearInterval(poll);
        lastSimCell = -1;
      }
    } catch (e) { clearInterval(poll); }
  }, 250);
}

$('#btn-dev-send').onclick = async () => {
  if (!state.result) { setStatus('Convert some text first (Convert tab).', 'bad'); return; }
  try {
    await post('/api/device/send', { port: $('#port').value, cells: state.result.cells, delay: +$('#delay').value });
    setStatus('Sending to Braille cell…', 'ok');
    watch();
  } catch (e) { setStatus(e.message, 'bad'); }
};
$('#btn-dev-stop').onclick = () => post('/api/device/stop', {}).catch(() => {});
$('#btn-test-send').onclick = async () => {
  try {
    await post('/api/device/send', { port: $('#port').value, cells: [state.testCell], delay: 0.5 });
    setStatus('Sent.', 'ok');
    updateSimulator(state.testCell);
    watch();
  } catch (e) { setStatus(e.message, 'bad'); }
};
$('#btn-test-clear').onclick = () => setTestDots(0);

// Presets
$('#p-dot1').onclick = () => setTestDots(1);
$('#p-dot12').onclick = () => setTestDots(3);
$('#p-dot14').onclick = () => setTestDots(9);
$('#p-full').onclick = () => setTestDots(63);

// Hardware button simulation (GPIO 32 BTN_NEXT)
$('#btn-hw-next').onclick = () => {
  flashSerialLed();
  playBuzzer();
  if (state.result && state.result.cells && state.result.cells.length) {
    showCell((state.idx + 1) % state.result.cells.length);
  } else {
    const patterns = [1, 3, 7, 15, 31, 63, 0];
    const nextCode = patterns[(patterns.indexOf(state.testCell) + 1) % patterns.length];
    setTestDots(nextCode);
  }
};

/* ---------- decode ---------- */
async function decodeBraille() {
  const input = $('#braille-input').value.trim();
  if (!input) { $('#decode-res').textContent = 'Enter Braille Unicode or ASCII first.'; return; }
  try {
    const r = await post('/api/decode', { braille: input, lang: $('#lang').value === 'hi' ? 'hi' : 'en' });
    $('#decode-res').textContent = `Decoded: "${r.text}"`;
  } catch (e) {
    $('#decode-res').textContent = 'Decode error: ' + e.message;
  }
}
const btnDecode = $('#btn-decode');
if (btnDecode) btnDecode.onclick = decodeBraille;
const inpBraille = $('#braille-input');
if (inpBraille) inpBraille.addEventListener('keydown', e => { if (e.key === 'Enter') decodeBraille(); });

/* ---------- init ---------- */
(async function init() {
  const lg = $('#logo'); lg.replaceChildren(...cellSVG(0b101101, 26).childNodes);
  drawEditor($('#test-cell'), 'testCell');
  initSimulatorChannels();
  updateSimulator(0);
  try {
    const h = await api('/api/health');
    $('#ocr-note').textContent = h.ocr.available ? 'Languages installed for OCR: ' + h.ocr.languages.filter(l => ['eng', 'hin'].includes(l)).join(', ') : 'OCR is not available: ' + h.ocr.hint;
    $('#file').disabled = !h.ocr.available;
    refreshPorts();
  } catch (e) { setStatus(e.message, 'bad'); }
})();
