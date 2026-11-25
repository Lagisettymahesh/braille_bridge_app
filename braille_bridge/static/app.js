'use strict';
const $ = s => document.querySelector(s);
const DOTPOS = [[20, 18], [20, 45], [20, 72], [40, 18], [40, 45], [40, 72]];
const state = {
  result: null,
  idx: 0,
  timer: null,
  quiz: null,
  answered: false,
  editCell: 0,
  testCell: 0,
  stats: { conversions: 1, chars: 1240 },
  revisionOnly: false
};

/* ---------- helpers ---------- */
function setStatus(msg, kind) {
  const s = $('#status');
  if (s) {
    s.textContent = msg || '';
    s.className = 'status-bar ' + (kind || '');
  }
}
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
function updateWaveform(mode) {
  const wf = $('#va-waveform');
  if (!wf) return;
  wf.classList.remove('speaking', 'paused');
  if (mode === 'speaking') {
    wf.classList.add('speaking');
  } else if (mode === 'paused') {
    wf.classList.add('paused');
  }
}

function speak(text, lang, onDone) {
  const liveEl = $('#va-aria-live');
  if (liveEl) liveEl.textContent = text || '';
  if (!('speechSynthesis' in window) || !text) {
    if (onDone) onDone();
    return;
  }
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang || ($('#lang') && $('#lang').value === 'hi' ? 'hi-IN' : 'en-IN');
  state.isSpeaking = true;
  updateWaveform('speaking');
  u.onend = () => {
    state.isSpeaking = false;
    updateWaveform(window.__vaListening ? 'active' : 'paused');
    if (onDone) onDone();
  };
  u.onerror = () => {
    state.isSpeaking = false;
    updateWaveform(window.__vaListening ? 'active' : 'paused');
    if (onDone) onDone();
  };
  speechSynthesis.speak(u);
}

function playToneCue(kind) {
  const chk = $('#sound-on');
  if (chk && !chk.checked) return;
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    const now = audioCtx.currentTime;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    if (kind === 'ready') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(520, now);
      osc.frequency.exponentialRampToValueAtTime(680, now + 0.12);
      gain.gain.setValueAtTime(0.05, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);
      osc.start(now);
      osc.stop(now + 0.14);
    } else if (kind === 'success') {
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.setValueAtTime(554, now + 0.08);
      osc.frequency.setValueAtTime(659, now + 0.16);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
      osc.start(now);
      osc.stop(now + 0.28);
    } else if (kind === 'cancel') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.exponentialRampToValueAtTime(320, now + 0.14);
      gain.gain.setValueAtTime(0.05, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
      osc.start(now);
      osc.stop(now + 0.15);
    }
  } catch (e) {}
}
function download(name, text, type) {
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; a.click(); URL.revokeObjectURL(a.href);
}
function el(tag, props = {}, ...kids) { const e = Object.assign(document.createElement(tag), props); kids.forEach(k => e.append(k)); return e; }

/* ---------- tabs ---------- */
const TABS = ['home', 'dashboard', 'convert', 'pdf', 'learn', 'sim', 'device'];
function showTab(name) {
  TABS.forEach(t => {
    const btn = $('#t-' + t);
    const panel = $('#p-' + t);
    const sel = (t === name);
    if (btn) {
      btn.setAttribute('aria-selected', sel ? 'true' : 'false');
      btn.tabIndex = sel ? 0 : -1;
    }
    if (panel) {
      panel.hidden = !sel;
    }
  });

  const links = $('#main-nav-links');
  if (links) links.classList.remove('mobile-open');

  if (name === 'learn') { refreshSets(); if (!state.quiz) nextQuestion(); }
  if (name === 'sim') updateSimulator(state.testCell || 0);
  if (name === 'device') refreshPorts();
  if (name === 'dashboard') updateDashboard();
  setStatus('');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

TABS.forEach((t, i) => {
  const btn = $('#t-' + t);
  if (btn) {
    btn.addEventListener('click', () => showTab(t));
    btn.addEventListener('keydown', e => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        const n = TABS[(i + (e.key === 'ArrowRight' ? 1 : TABS.length - 1)) % TABS.length];
        showTab(n);
        const nextBtn = $('#t-' + n);
        if (nextBtn) nextBtn.focus();
      }
    });
  }
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
  ['#btn-copy', '#btn-brf', '#btn-txt', '#btn-speak'].forEach(b => {
    if ($(b)) $(b).disabled = false;
  });

  // Update session metrics
  state.stats.conversions += 1;
  state.stats.chars += (r.count || 0);
  if ($('#dash-conversions')) $('#dash-conversions').textContent = state.stats.conversions;
  if ($('#dash-chars')) $('#dash-chars').textContent = state.stats.chars.toLocaleString();

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

function updateCharCount() {
  const val = $('#text') ? $('#text').value : '';
  const words = val.trim() ? val.trim().split(/\s+/).length : 0;
  const badge = $('#char-count-badge');
  if (badge) badge.textContent = `${val.length} character${val.length === 1 ? '' : 's'} · ${words} word${words === 1 ? '' : 's'}`;
}
if ($('#text')) $('#text').addEventListener('input', updateCharCount);

if ($('#btn-toggle-font')) {
  $('#btn-toggle-font').onclick = () => {
    const u = $('#unicode');
    if (u) u.classList.toggle('large-font');
  };
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
  const pageRange = ($('#pdf-page-range') && $('#pdf-page-range').value) || 'all';
  fd.append('page_range', pageRange);
  fd.append('ocr_lang', ($('#ocr-lang') && $('#ocr-lang').value) || 'eng');

  try {
    const r = await api('/api/upload-pdf', { method: 'POST', body: fd });
    const warnEl = $('#doc-warning');
    if (warnEl) {
      if (r.warning) {
        warnEl.textContent = '⚠️ ' + r.warning;
        warnEl.hidden = false;
      } else {
        warnEl.hidden = true;
      }
    }
    const statsEl = $('#doc-stats');
    if (statsEl) {
      statsEl.textContent = `📄 ${r.filename}: ${r.chars} chars across ${r.pages} of ${r.total_pages} page(s) · Method: ${r.method}`;
    }

    if (!r.text && r.is_scanned) {
      const w = `Scanned PDF detected (${r.pages} page(s)). No digital text could be extracted.`;
      setStatus(w, 'bad');
      speak('Scanned PDF detected with no digital text.');
      return;
    }
    $('#text').value = r.text || '';
    if ($('#pdf-preview-text')) $('#pdf-preview-text').value = r.text || '';
    if ($('#btn-convert-pdf-text')) $('#btn-convert-pdf-text').disabled = !r.text;
    updateCharCount();

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

// Drag & drop upload zone
const dropzone = $('#pdf-dropzone');
if (dropzone) {
  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, e => {
      e.preventDefault(); e.stopPropagation();
      dropzone.classList.add('dragover');
    }, false);
  });
  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, e => {
      e.preventDefault(); e.stopPropagation();
      dropzone.classList.remove('dragover');
    }, false);
  });
  dropzone.addEventListener('drop', e => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files && files[0]) handlePdfUpload(files[0]);
  }, false);
}

if ($('#btn-convert-pdf-text')) {
  $('#btn-convert-pdf-text').onclick = () => {
    const txt = $('#pdf-preview-text')?.value || '';
    if (txt) {
      $('#text').value = txt;
      showTab('convert');
      convert();
    }
  };
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

/* ---------- Voice-Controlled File Navigation & Management ---------- */
const vaFileState = {
  mode: 'IDLE', // 'IDLE' | 'LISTING' | 'AWAITING_CONFIRMATION' | 'PROCESSING'
  currentFolder: 'documents',
  currentSubpath: '',
  parentPath: null,
  canGoBack: false,
  candidates: [],
  selectedFile: null,
  page: 1,
  totalPages: 1,
  lastSpokenPrompt: ''
};

async function browseVoiceFolder(folder, subpath = '', page = 1, speakOut = true) {
  const fDesc = folder || 'documents';
  setStatus(`Browsing ${fDesc} folder…`);
  try {
    const r = await api(`/api/files/browse?folder=${encodeURIComponent(folder || 'documents')}&subpath=${encodeURIComponent(subpath || '')}&page=${page}&page_size=6`);
    if (!r.ok) throw new Error(r.error || 'Cannot open folder');

    vaFileState.mode = 'LISTING';
    vaFileState.currentFolder = r.folder_name;
    vaFileState.currentSubpath = subpath;
    vaFileState.canGoBack = r.can_go_back;
    vaFileState.parentPath = r.parent_path;
    vaFileState.candidates = r.files || [];
    vaFileState.page = r.page || 1;
    vaFileState.totalPages = r.total_pages || 1;
    vaFileState.lastSpokenPrompt = r.spoken_summary;

    renderFileExplorerUI(r);
    renderCandidateChips(r.files);

    if (speakOut && r.spoken_summary) {
      announce(r.spoken_summary, () => playToneCue('ready'));
    }
  } catch (e) {
    setStatus('Folder navigation error: ' + e.message, 'bad');
    announce('Could not open folder ' + fDesc + ': ' + e.message);
  }
}

async function searchVoiceFiles(query, folder = '', speakOut = true) {
  setStatus(`Searching files for "${query}"…`);
  try {
    const r = await api(`/api/files/search?query=${encodeURIComponent(query || '')}&folder=${encodeURIComponent(folder || '')}&limit=6`);
    if (!r.ok) throw new Error(r.error || 'Search failed');

    vaFileState.mode = 'LISTING';
    vaFileState.candidates = r.files || [];
    vaFileState.page = 1;
    vaFileState.totalPages = 1;
    vaFileState.lastSpokenPrompt = r.spoken_summary;

    renderFileExplorerUI({
      folder_name: `Search: "${query}"`,
      files: r.files,
      can_go_back: true,
      total_files: r.found,
      page: 1,
      total_pages: 1
    });
    renderCandidateChips(r.files);

    if (speakOut && r.spoken_summary) {
      announce(r.spoken_summary, () => playToneCue('ready'));
    }
  } catch (e) {
    setStatus('File search error: ' + e.message, 'bad');
    announce('Error searching files: ' + e.message);
  }
}

function selectCandidateFile(file) {
  if (!file) return;
  vaFileState.selectedFile = file;
  vaFileState.mode = 'AWAITING_CONFIRMATION';

  const promptText = `You selected ${file.filename}. Shall I upload it?`;
  vaFileState.lastSpokenPrompt = promptText;

  const confirmBox = $('#va-confirm-box');
  const confirmPrompt = $('#va-confirm-prompt');
  if (confirmBox && confirmPrompt) {
    confirmPrompt.textContent = promptText;
    confirmBox.hidden = false;
  }

  const feConfirmBox = $('#fe-confirm-box');
  const feConfirmPrompt = $('#fe-confirm-prompt');
  if (feConfirmBox && feConfirmPrompt) {
    feConfirmPrompt.textContent = promptText;
    feConfirmBox.hidden = false;
  }

  document.querySelectorAll('.va-file-item').forEach(it => {
    it.classList.toggle('selected', it.dataset.path === file.path);
  });

  announce(promptText, () => playToneCue('ready'));
}

async function confirmUploadAndConvert() {
  if (!vaFileState.selectedFile) return;
  const file = vaFileState.selectedFile;
  vaFileState.mode = 'PROCESSING';

  if ($('#va-confirm-box')) $('#va-confirm-box').hidden = true;
  if ($('#fe-confirm-box')) $('#fe-confirm-box').hidden = true;

  const startingMsg = `Uploading and processing ${file.filename}…`;
  setStatus(startingMsg);
  announce(startingMsg);

  try {
    const lang = ($('#lang') && $('#lang').value) || 'auto';
    const grade = ($('#grade') && $('#grade').value) || 1;
    const pageRange = ($('#pdf-page-range') && $('#pdf-page-range').value) || 'all';
    const ocrLang = ($('#ocr-lang') && $('#ocr-lang').value) || 'eng';

    const r = await api('/api/files/load', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: file.path,
        lang: lang,
        grade: grade,
        page_range: pageRange,
        ocr_lang: ocrLang
      })
    });

    if (!r.ok) throw new Error(r.error || 'Failed to load and process file');

    $('#text').value = r.text || '';
    if ($('#pdf-preview-text')) $('#pdf-preview-text').value = r.text || '';
    if ($('#btn-convert-pdf-text')) $('#btn-convert-pdf-text').disabled = !r.text;
    updateCharCount();

    if ($('#doc-stats')) {
      $('#doc-stats').textContent = `📄 ${r.filename}: ${r.chars} chars across ${r.pages} of ${r.total_pages} page(s) · Method: ${r.method}`;
    }

    if (r.conversion && r.conversion.cells) {
      applyConversionResult(r.conversion, `from "${r.filename}"`);
    } else {
      await convert();
    }

    showTab('convert');
    playToneCue('success');

    const doneMsg = r.spoken_summary || `Successfully processed ${r.filename} and converted normal text to Braille.`;
    setStatus(doneMsg, 'ok');
    announce(doneMsg);

    vaFileState.mode = 'IDLE';
    vaFileState.selectedFile = null;
  } catch (err) {
    playToneCue('cancel');
    setStatus('Error processing document: ' + err.message, 'bad');
    announce('Error processing document: ' + err.message);
    vaFileState.mode = 'LISTING';
  }
}

function cancelSelection() {
  vaFileState.selectedFile = null;
  if ($('#va-confirm-box')) $('#va-confirm-box').hidden = true;
  if ($('#fe-confirm-box')) $('#fe-confirm-box').hidden = true;
  document.querySelectorAll('.va-file-item').forEach(it => it.classList.remove('selected'));

  playToneCue('cancel');
  const msg = 'Upload cancelled. Which file would you like to select?';
  announce(msg);
  vaFileState.mode = vaFileState.candidates.length > 0 ? 'LISTING' : 'IDLE';
}

function repeatVoicePrompt() {
  if (vaFileState.mode === 'AWAITING_CONFIRMATION' && vaFileState.selectedFile) {
    announce(`You selected ${vaFileState.selectedFile.filename}. Shall I upload it?`, () => playToneCue('ready'));
  } else if (vaFileState.mode === 'LISTING' && vaFileState.candidates.length > 0) {
    if (vaFileState.lastSpokenPrompt) {
      announce(vaFileState.lastSpokenPrompt, () => playToneCue('ready'));
    } else {
      const lines = vaFileState.candidates.map(f => `Number ${f.id}: ${f.filename}`);
      announce(`Available files: ${lines.join('. ')}. Which one would you like?`, () => playToneCue('ready'));
    }
  } else {
    const greeting = getGreeting();
    announce(`${greeting} Welcome to Braille Bridge. Which file would you like to convert? You can say: Find my project PDF, or open Documents, Downloads, or Desktop.`);
  }
}

function goBackVoiceFolder() {
  if (vaFileState.canGoBack && vaFileState.parentPath) {
    browseVoiceFolder(vaFileState.parentPath, '', 1, true);
  } else if (vaFileState.currentFolder !== 'documents') {
    browseVoiceFolder('documents', '', 1, true);
  } else {
    announce('Already at the root Documents folder.');
  }
}

function resolveCandidateSelection(phrase) {
  if (!vaFileState.candidates || !vaFileState.candidates.length) {
    announce('No files are currently listed. Say open Documents or find my project PDF first.');
    return;
  }
  const phraseLower = phrase.toLowerCase().trim();
  const count = vaFileState.candidates.length;

  const ordMap = {
    'first': 0, '1st': 0, 'one': 0, '1': 0,
    'second': 1, '2nd': 1, 'two': 1, '2': 1,
    'third': 2, '3rd': 2, 'three': 2, '3': 2,
    'fourth': 3, '4th': 3, 'four': 3, '4': 3,
    'fifth': 4, '5th': 4, 'five': 4, '5': 4,
    'sixth': 5, '6th': 5, 'six': 5, '6': 5,
  };

  let selectedIdx = null;
  if (phraseLower.includes('last')) {
    selectedIdx = count - 1;
  } else {
    const words = phraseLower.split(/\s+/);
    for (const w of words) {
      if (ordMap[w] !== undefined && ordMap[w] < count) {
        selectedIdx = ordMap[w];
        break;
      }
    }
  }

  if (selectedIdx === null) {
    let bestScore = 0;
    vaFileState.candidates.forEach((cand, idx) => {
      const baseName = cand.filename.toLowerCase().replace(/\.[^/.]+$/, '');
      if (phraseLower.includes(baseName)) {
        if (baseName.length > bestScore) {
          bestScore = baseName.length;
          selectedIdx = idx;
        }
      }
    });
  }

  if (selectedIdx !== null && vaFileState.candidates[selectedIdx]) {
    selectCandidateFile(vaFileState.candidates[selectedIdx]);
  } else {
    announce(`I didn't catch which file you wanted. Please say number 1 through ${count}, or speak the filename.`);
  }
}

function renderCandidateChips(files) {
  const container = $('#va-candidates-chips');
  const area = $('#va-candidates-area');
  if (!container || !area) return;
  if (!files || !files.length) {
    area.hidden = true;
    return;
  }
  area.hidden = false;
  container.replaceChildren();
  files.forEach(f => {
    const chip = el('button', {
      type: 'button',
      className: 'va-chip',
      style: 'font-size:0.82rem; font-weight:600; display:inline-flex; align-items:center; gap:0.35rem;',
      title: f.path
    }, el('span', { className: 'va-ordinal-badge', style: 'width:20px; height:20px; font-size:0.75rem;' }, String(f.id)), ' ' + f.filename);
    chip.onclick = () => selectCandidateFile(f);
    container.append(chip);
  });
}

function renderFileExplorerUI(data) {
  const breadcrumbs = $('#fe-current-folder');
  if (breadcrumbs) breadcrumbs.textContent = data.folder_name || 'Documents';

  const backBtn = $('#fe-btn-back');
  if (backBtn) backBtn.disabled = !data.can_go_back;

  const list = $('#fe-file-list');
  if (!list) return;
  list.replaceChildren();

  if (!data.files || !data.files.length) {
    list.append(el('p', { className: 'hint', style: 'grid-column: 1/-1; padding: 1rem;' },
      `No supported document files found in ${data.folder_name}. Try another folder above.`));
    if ($('#fe-pagination')) $('#fe-pagination').hidden = true;
    return;
  }

  data.files.forEach(f => {
    const item = el('button', {
      type: 'button',
      className: 'va-file-item' + (vaFileState.selectedFile && vaFileState.selectedFile.path === f.path ? ' selected' : ''),
      dataset: { path: f.path }
    },
      el('span', { className: 'va-ordinal-badge' }, String(f.id)),
      el('div', { className: 'va-file-info' },
        el('div', { className: 'va-file-name' }, f.filename),
        el('div', { className: 'va-file-meta' }, `${f.size_str || ''} · ${f.type.toUpperCase()}`)
      ),
      el('span', { style: 'font-size:0.8rem; font-weight:600; color:var(--brand-secondary); margin-left:auto;' }, 'Select')
    );
    item.onclick = () => selectCandidateFile(f);
    list.append(item);
  });

  const pag = $('#fe-pagination');
  if (pag) {
    pag.hidden = (data.total_pages <= 1);
    const info = $('#fe-page-info');
    if (info) info.textContent = `Page ${data.page || 1} of ${data.total_pages || 1}`;
    const prevBtn = $('#fe-btn-prev-page');
    if (prevBtn) prevBtn.disabled = (data.page <= 1);
    const nextBtn = $('#fe-btn-next-page');
    if (nextBtn) nextBtn.disabled = (data.page >= data.total_pages);
  }
}

// Explorer button attachments
if ($('#btn-quick-desktop') || $('#fe-btn-desktop')) {
  const fnDesk = () => { showTab('pdf'); browseVoiceFolder('desktop'); };
  if ($('#btn-quick-desktop')) $('#btn-quick-desktop').onclick = fnDesk;
  if ($('#fe-btn-desktop')) $('#fe-btn-desktop').onclick = fnDesk;
}
if ($('#btn-quick-downloads') || $('#fe-btn-downloads')) {
  const fnDown = () => { showTab('pdf'); browseVoiceFolder('downloads'); };
  if ($('#btn-quick-downloads')) $('#btn-quick-downloads').onclick = fnDown;
  if ($('#fe-btn-downloads')) $('#fe-btn-downloads').onclick = fnDown;
}
if ($('#btn-quick-documents') || $('#fe-btn-documents')) {
  const fnDocs = () => { showTab('pdf'); browseVoiceFolder('documents'); };
  if ($('#btn-quick-documents')) $('#btn-quick-documents').onclick = fnDocs;
  if ($('#fe-btn-documents')) $('#fe-btn-documents').onclick = fnDocs;
}
if ($('#fe-btn-capstone')) $('#fe-btn-capstone').onclick = () => { showTab('pdf'); browseVoiceFolder('capston'); };
if ($('#fe-btn-back')) $('#fe-btn-back').onclick = () => goBackVoiceFolder();
if ($('#fe-btn-repeat')) $('#fe-btn-repeat').onclick = () => repeatVoicePrompt();

if ($('#fe-btn-search')) {
  $('#fe-btn-search').onclick = () => {
    const q = ($('#fe-search-input') && $('#fe-search-input').value.trim()) || '';
    if (q) searchVoiceFiles(q);
  };
}
if ($('#fe-search-input')) {
  $('#fe-search-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      const q = e.target.value.trim();
      if (q) searchVoiceFiles(q);
    }
  });
}
if ($('#fe-btn-voice-search')) {
  $('#fe-btn-voice-search').onclick = () => {
    showTab('pdf');
    announce('What file name would you like to search for?');
  };
}
if ($('#fe-btn-prev-page')) {
  $('#fe-btn-prev-page').onclick = () => {
    if (vaFileState.page > 1) browseVoiceFolder(vaFileState.currentFolder, vaFileState.currentSubpath, vaFileState.page - 1);
  };
}
if ($('#fe-btn-next-page')) {
  $('#fe-btn-next-page').onclick = () => {
    if (vaFileState.page < vaFileState.totalPages) browseVoiceFolder(vaFileState.currentFolder, vaFileState.currentSubpath, vaFileState.page + 1);
  };
}
if ($('#btn-va-confirm-yes')) $('#btn-va-confirm-yes').onclick = confirmUploadAndConvert;
if ($('#btn-va-confirm-no')) $('#btn-va-confirm-no').onclick = cancelSelection;
if ($('#btn-fe-confirm-yes')) $('#btn-fe-confirm-yes').onclick = confirmUploadAndConvert;
if ($('#btn-fe-confirm-no')) $('#btn-fe-confirm-no').onclick = cancelSelection;

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
        const msg = `${greeting} Welcome to Braille Bridge. Which file would you like to convert? You can say: Find my project PDF, or open Documents, Downloads, or Desktop.`;
        announce(msg, () => {
          playToneCue('ready');
          startListening();
        });
      } else {
        startListening();
      }
    } else {
      stopListening();
      updateWaveform('paused');
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
        window.__vaListening = true;
        if (!state.isSpeaking) updateWaveform('active');
        if (statusText) statusText.textContent = 'Listening for commands…';
      };

      recognition.onresult = event => {
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
        window.__vaListening = false;
        if (!state.isSpeaking) updateWaveform('paused');
      };

      recognition.onend = () => {
        isListening = false;
        window.__vaListening = false;
        if (!state.isSpeaking) updateWaveform('paused');
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
      window.__vaListening = false;
      if (!state.isSpeaking) updateWaveform('paused');
    }
  }

  function stopListening() {
    clearTimeout(restartTimer);
    if (recognition) {
      try { recognition.abort(); } catch (e) {}
      recognition = null;
    }
    isListening = false;
    window.__vaListening = false;
    if (!state.isSpeaking) updateWaveform('paused');
  }

  function processCommand(phrase) {
    if (!phrase) return;
    if (transcriptEl) transcriptEl.innerHTML = `Heard: "<strong>${phrase}</strong>"`;

    // 1. If currently waiting for user confirmation to upload:
    if (vaFileState.mode === 'AWAITING_CONFIRMATION') {
      if (phrase === 'yes' || phrase === 'sure' || phrase === 'yeah' || phrase.includes('yes upload') || phrase.includes('confirm') || phrase.includes('upload it') || phrase.includes('please do') || phrase === 'upload') {
        confirmUploadAndConvert();
        return;
      }
      if (phrase === 'no' || phrase.includes('cancel') || phrase.includes('wrong') || phrase.includes("don't upload") || phrase.includes('stop')) {
        cancelSelection();
        return;
      }
      if (phrase.includes('repeat') || phrase.includes('again')) {
        repeatVoicePrompt();
        return;
      }
    }

    // 2. Stop Speaking / Silence
    if (phrase.includes('stop speaking') || phrase.includes('stop speech') || phrase.includes('quiet') ||
        phrase.includes('silence') || phrase.includes('shut up') || phrase === 'stop') {
      speechSynthesis.cancel();
      state.isSpeaking = false;
      if (statusText) statusText.textContent = 'Speech paused. Listening for commands…';
      startListening();
      return;
    }

    // 3. Repeat Instruction or File List
    if (phrase.includes('repeat') || phrase.includes('again') || phrase.includes('what did you say') || phrase.includes('read files') || phrase.includes('read again')) {
      repeatVoicePrompt();
      return;
    }

    // 4. Cancel
    if (phrase === 'cancel' || phrase.includes('cancel selection')) {
      cancelSelection();
      return;
    }

    // 5. Go Back / Previous Folder
    if (phrase.includes('go back') || phrase.includes('previous folder') || phrase.includes('parent folder') || phrase === 'back') {
      goBackVoiceFolder();
      return;
    }

    // 6. Pagination in file list
    if (phrase.includes('next page')) {
      if (vaFileState.page < vaFileState.totalPages) {
        browseVoiceFolder(vaFileState.currentFolder, vaFileState.currentSubpath, vaFileState.page + 1);
      } else {
        announce('Already on the last page of files.');
      }
      return;
    }
    if (phrase.includes('previous page')) {
      if (vaFileState.page > 1) {
        browseVoiceFolder(vaFileState.currentFolder, vaFileState.currentSubpath, vaFileState.page - 1);
      } else {
        announce('Already on the first page of files.');
      }
      return;
    }

    // 7. If in LISTING state, test for candidate selection (e.g. "select the second one", "number two")
    if (vaFileState.mode === 'LISTING') {
      const isSelectIntent = phrase.includes('select') || phrase.includes('choose') || phrase.includes('open') || phrase.includes('pick') ||
                             phrase.includes('first') || phrase.includes('second') || phrase.includes('third') || phrase.includes('fourth') ||
                             phrase.includes('fifth') || phrase.includes('sixth') || phrase.includes('number') ||
                             phrase.includes('1') || phrase.includes('2') || phrase.includes('3') || phrase.includes('4') || phrase.includes('5') ||
                             phrase.includes('last');
      if (isSelectIntent) {
        resolveCandidateSelection(phrase);
        return;
      }
    }

    // 8. Open specific folders: Documents, Downloads, Desktop, Capstone
    if (phrase.includes('open document') || phrase.includes('in documents') || phrase === 'documents' || phrase.includes('show documents')) {
      showTab('pdf');
      browseVoiceFolder('documents');
      return;
    }
    if (phrase.includes('open download') || phrase.includes('in downloads') || phrase === 'downloads' || phrase.includes('show downloads')) {
      showTab('pdf');
      browseVoiceFolder('downloads');
      return;
    }
    if (phrase.includes('open desktop') || phrase.includes('in desktop') || phrase === 'desktop' || phrase.includes('show desktop')) {
      showTab('pdf');
      browseVoiceFolder('desktop');
      return;
    }
    if (phrase.includes('open capston') || phrase.includes('open capstone') || phrase.includes('capston')) {
      showTab('pdf');
      browseVoiceFolder('capston');
      return;
    }

    // 9. Search / Find: "Find my project PDF", "Search for report"
    if (phrase.startsWith('find ') || phrase.startsWith('search ') || phrase.includes('find my') || phrase.includes('search for') || phrase.includes('project pdf')) {
      showTab('pdf');
      let q = phrase.replace(/^(find\s+my|find|search\s+for|search)\s+/, '').trim();
      if (!q || q === 'pdf') q = 'project';
      searchVoiceFiles(q);
      return;
    }

    // 10. General "upload pdf" or "upload file" prompt
    if (phrase.includes('upload pdf') || phrase.includes('upload a pdf') || phrase.includes('upload document') || phrase.includes('choose file')) {
      showTab('pdf');
      announce('Which file would you like to convert? You can say: Find my project PDF, or open Documents, Downloads, or Desktop.', () => {
        playToneCue('ready');
      });
      return;
    }

    // 11. Hardware Self Test / Dot Test
    if (phrase.includes('test dot') || phrase.includes('hardware test') || phrase.includes('test hardware') || phrase.includes('check cell')) {
      showTab('device');
      announce('Running 6-dot hardware diagnostic self-test.', () => {
        runHardwareTest();
      });
      return;
    }

    // 12. Player Controls: Next, Back, Play, Pause
    if (phrase.includes('next cell') || phrase === 'next' || phrase === 'forward') {
      $('#p-next').click();
      announce('Next cell: ' + $('#cur').textContent);
      return;
    }
    if (phrase.includes('previous cell') || phrase === 'previous' || phrase === 'back') {
      $('#p-prev').click();
      announce('Previous cell: ' + $('#cur').textContent);
      return;
    }
    if (phrase.includes('play braille') || phrase === 'play' || phrase === 'start player') {
      $('#p-play').click();
      announce('Playing Braille stream.');
      return;
    }
    if (phrase.includes('pause braille') || phrase === 'pause' || phrase === 'pause player') {
      stopPlay();
      announce('Paused Braille player.');
      return;
    }

    // 13. Navigation Commands
    if (phrase.includes('open website') || phrase.includes('home') || phrase.includes('main page')) {
      showTab('home');
      announce('Showing Braille Bridge homepage.');
      return;
    }
    if (phrase.includes('dashboard') || phrase.includes('stats') || phrase.includes('overview')) {
      showTab('dashboard');
      announce('Opening Dashboard.');
      return;
    }
    if (phrase.includes('open pdf') || phrase.includes('pdf page') || phrase.includes('document page')) {
      showTab('pdf');
      announce('Opening PDF and document upload.');
      return;
    }
    if (phrase.includes('open learn') || phrase.includes('learn') || phrase.includes('quiz') || phrase.includes('practice') || phrase.includes('study')) {
      showTab('learn');
      announce('Opening Braille Learning Center.');
      return;
    }
    if (phrase.includes('open sim') || phrase.includes('simulator') || phrase.includes('virtual cell')) {
      showTab('sim');
      announce('Opening Virtual Braille Mechanical Simulator.');
      return;
    }
    if (phrase.includes('open device') || phrase.includes('device') || phrase.includes('hardware')) {
      showTab('device');
      announce('Opening Physical Hardware Controller.');
      return;
    }

    // 14. Convert Normal Text to Braille Text
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

    // 15. Read Aloud
    if (phrase.includes('read aloud') || phrase.includes('read text') || phrase.includes('read braille') ||
        phrase.includes('speak text') || phrase.includes('read this') || phrase.includes('read it')) {
      const text = $('#text').value;
      if (!text.trim()) {
        announce('No text to read aloud. Please upload a PDF or enter text first.');
      } else {
        announce('Reading text aloud: ' + text);
      }
      return;
    }

    // 16. Clear
    if (phrase.includes('clear') || phrase.includes('reset') || phrase.includes('erase')) {
      $('#text').value = '';
      announce('Text cleared.');
      return;
    }

    // 17. Help
    if (phrase.includes('help') || phrase.includes('command') || phrase.includes('what can you do') || phrase.includes('options')) {
      announce('You can say: Find my project PDF, Open Documents, Open Downloads, Select the second one, Upload it, Convert, Stop speaking, Test dots, Next cell, Play, Read aloud, or Clear.');
      return;
    }

    // 18. Dictate / Type explicitly
    if (phrase.startsWith('type ') || phrase.startsWith('write ') || phrase.startsWith('dictate ')) {
      const dictatedText = phrase.replace(/^(type|write|dictate)\s+/, '').trim();
      if (dictatedText) {
        $('#text').value += (($('#text').value ? ' ' : '') + dictatedText);
        if (transcriptEl) transcriptEl.innerHTML = `Typed: "<em>${dictatedText}</em>"`;
        announce('Added text: ' + dictatedText);
      }
      return;
    }

    if (transcriptEl) {
      transcriptEl.innerHTML = `Heard: "<em>${phrase}</em>" &nbsp;·&nbsp; <small style="color:var(--text-muted)">Say <strong>"Help"</strong> or speak a command</small>`;
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
    const promptMessage = `${greeting} Welcome to Braille Bridge. Which file would you like to convert? You can say: Find my project PDF, or open Documents, Downloads, or Desktop.`;

    if (statusText) statusText.textContent = 'Voice Assistant Active · Listening for commands…';
    if (transcriptEl) transcriptEl.innerHTML = `<strong>${promptMessage}</strong>`;

    announce(promptMessage, () => {
      playToneCue('ready');
      startListening();
    });
  }

  setTimeout(autoWelcomeAndAsk, 600);

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
state.revisionOnly = false;

async function refreshSets() {
  try {
    const u = encodeURIComponent(user());
    const sets = await api('/api/sets?user=' + u);
    const sel = $('#set'), cur = sel.value;
    sel.replaceChildren(...sets.map(s => el('option', { value: s.id }, `[${s.level}] ${s.title} (${Math.round(s.mastery * 100)}%)`)));
    if (cur && sets.some(x => x.id === cur)) sel.value = cur;
    const s = sets.find(x => x.id === sel.value) || sets[0];
    $('#meter-bar').style.width = Math.round(s.mastery * 100) + '%';
    $('#meter-txt').textContent = `Mastered ${Math.round(s.mastery * s.items)} of ${s.items} characters.`;

    const totalRev = sets.reduce((acc, curr) => acc + (curr.revision_count || 0), 0);
    const badgeEl = $('#rev-badge');
    if (badgeEl) badgeEl.textContent = totalRev;

    // Load stats
    try {
      const stats = await api('/api/learning/stats?user=' + u);
      const stEl = $('#stats-summary');
      if (stEl) {
        stEl.textContent = `${stats.total_attempts} attempts · ${stats.accuracy}% accuracy · ${stats.mastered_items} characters mastered`;
      }
    } catch (e) {}

    $('#prog').replaceChildren(...sets.map(x => el('tr', {},
      el('td', {}, `[${x.level}] ${x.title}`),
      el('td', {}, Math.round(x.mastery * 100) + '%'),
      el('td', {}, String(x.attempts)),
      el('td', {}, x.attempts ? Math.round(100 * x.correct / x.attempts) + '%' : '—')
    )));
  } catch (e) { setStatus(e.message, 'bad'); }
}

async function nextQuestion() {
  const q = $('#quiz'); state.answered = false; state.editCell = 0;
  try {
    const revParam = state.revisionOnly ? '&revision=true' : '';
    const d = await api(`/api/quiz/next?user=${encodeURIComponent(user())}&set=${$('#set').value || 'en-beginner'}&mode=${mode()}${revParam}` +
      (state.quiz ? '&last=' + encodeURIComponent(state.quiz.item) : ''));
    state.quiz = d; q.replaceChildren();
    const fb = el('p', { className: 'feedback', id: 'fb' });

    if (state.revisionOnly) {
      q.append(el('div', { style: 'background:#fee2e2; color:#991b1b; padding:0.3rem 0.6rem; border-radius:4px; font-size:0.8rem; font-weight:600; margin-bottom:0.6rem;' },
        '🔁 Revision Mode: Practicing previously missed item'));
    }

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
if ($('#btn-revise')) {
  $('#btn-revise').onclick = () => {
    state.revisionOnly = true;
    state.quiz = null;
    nextQuestion();
  };
}
$('#set').onchange = () => { state.revisionOnly = false; state.quiz = null; nextQuestion(); };
$('#user').onchange = () => { state.revisionOnly = false; state.quiz = null; refreshSets(); nextQuestion(); };
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

async function runHardwareTest() {
  const p = $('#port') ? $('#port').value : 'VIRTUAL';
  setStatus('Starting 6-dot hardware diagnostic self-test…', 'ok');
  try {
    await post('/api/device/test', { port: p });
    watch();
  } catch (e) {
    setStatus('Hardware test error: ' + e.message, 'bad');
  }
}
if ($('#btn-dev-test')) $('#btn-dev-test').onclick = runHardwareTest;

// Interactive dot click on mechanical simulator grid
document.querySelectorAll('#tactile-grid .tactile-pin').forEach(pin => {
  pin.style.cursor = 'pointer';
  pin.addEventListener('click', () => {
    const dotNum = parseInt(pin.dataset.dot, 10);
    if (dotNum >= 1 && dotNum <= 6) {
      const bit = 1 << (dotNum - 1);
      setTestDots(state.testCell ^ bit);
    }
  });
});
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

/* ---------- theme & dashboard & navigation extras ---------- */
function initTheme() {
  const saved = localStorage.getItem('braille_theme');
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = saved || (prefersDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
  const icon = $('#theme-icon');
  if (icon) icon.textContent = theme === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('braille_theme', next);
  const icon = $('#theme-icon');
  if (icon) icon.textContent = next === 'dark' ? '☀️' : '🌙';
}
if ($('#btn-theme-toggle')) $('#btn-theme-toggle').onclick = toggleTheme;

if ($('#btn-mobile-menu')) {
  $('#btn-mobile-menu').onclick = () => {
    const links = $('#main-nav-links');
    if (links) links.classList.toggle('mobile-open');
  };
}

// Quick navigation triggers
if ($('#brand-home-link')) $('#brand-home-link').onclick = () => showTab('home');
if ($('#btn-hero-convert')) $('#btn-hero-convert').onclick = () => showTab('convert');
if ($('#btn-hero-learn')) $('#btn-hero-learn').onclick = () => showTab('learn');
if ($('#btn-hero-sim')) $('#btn-hero-sim').onclick = () => showTab('sim');
if ($('#card-launch-convert')) $('#card-launch-convert').onclick = () => showTab('convert');
if ($('#card-launch-pdf')) $('#card-launch-pdf').onclick = () => showTab('pdf');
if ($('#card-launch-learn')) $('#card-launch-learn').onclick = () => showTab('learn');
if ($('#card-launch-sim')) $('#card-launch-sim').onclick = () => showTab('sim');
if ($('#btn-dash-quick-convert')) $('#btn-dash-quick-convert').onclick = () => showTab('convert');
if ($('#btn-dash-quick-upload')) $('#btn-dash-quick-upload').onclick = () => showTab('pdf');

// Hardware Ping
if ($('#btn-dev-ping')) {
  $('#btn-dev-ping').onclick = async () => {
    const port = $('#port') ? $('#port').value : 'VIRTUAL';
    setStatus(`Pinging device on port ${port}…`);
    try {
      const res = await post('/api/device/ping', { port });
      if (res.ok) setStatus(`Ping successful: ${res.response || 'Ready'}`, 'ok');
      else setStatus(`Ping failed: ${res.error || 'No response'}`, 'bad');
    } catch (e) {
      setStatus('Ping error: ' + e.message, 'bad');
    }
  };
}

async function updateDashboard() {
  try {
    const stats = await api('/api/learning/stats?user=' + encodeURIComponent(user()));
    if ($('#dash-mastery')) $('#dash-mastery').textContent = (stats.accuracy || 0) + '%';
    if ($('#dash-mastery-sub')) $('#dash-mastery-sub').textContent = `${stats.total_attempts} attempts · ${stats.mastered_items} mastered`;
    const dev = await api('/api/device/status');
    if ($('#dash-hardware-status')) $('#dash-hardware-status').textContent = dev.port === 'VIRTUAL' ? 'Virtual Ready' : (dev.running ? 'Transmitting' : 'Connected');
  } catch (e) {}
}

function initHeroCellAnimation() {
  const heroHost = $('#hero-cell-graphic');
  const heroChar = $('#hero-cell-char');
  if (!heroHost) return;
  const sequence = [
    { ch: 'B', cell: 3 },
    { ch: 'R', cell: 23 },
    { ch: 'A', cell: 1 },
    { ch: 'I', cell: 10 },
    { ch: 'L', cell: 7 },
    { ch: 'L', cell: 7 },
    { ch: 'E', cell: 17 }
  ];
  let heroIdx = 0;
  setInterval(() => {
    heroIdx = (heroIdx + 1) % sequence.length;
    const cur = sequence[heroIdx];
    heroHost.replaceChildren(cellSVG(cur.cell, 70, { numbers: true }));
    if (heroChar) heroChar.textContent = `Letter "${cur.ch}"`;
  }, 1600);
  heroHost.replaceChildren(cellSVG(sequence[0].cell, 70, { numbers: true }));
}

/* ---------- init ---------- */
(async function init() {
  initTheme();
  const lg = $('#logo');
  if (lg) lg.replaceChildren(...cellSVG(0b101101, 26).childNodes);
  drawEditor($('#test-cell'), 'testCell');
  initSimulatorChannels();
  updateSimulator(0);
  initHeroCellAnimation();
  updateCharCount();

  try {
    const h = await api('/api/health');
    if ($('#ocr-note')) $('#ocr-note').textContent = h.ocr.available ? 'Languages installed for OCR: ' + h.ocr.languages.filter(l => ['eng', 'hin'].includes(l)).join(', ') : 'OCR is not available: ' + h.ocr.hint;
    if ($('#file')) $('#file').disabled = !h.ocr.available;
    refreshPorts();
    updateDashboard();
  } catch (e) { setStatus(e.message, 'bad'); }
})();
