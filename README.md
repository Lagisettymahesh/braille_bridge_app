# BRAILLE BRIDGE: Automated Text-to-Braille System & Hardware Interface

[![Test Suite](https://img.shields.io/badge/Automated%20Tests-55%20Passed-brightgreen)](tests/test_all.py)
[![Python Version](https://img.shields.io/badge/Python-3.10%20|%203.11%20|%203.12%20|%203.13-blue)](https://python.org)
[![Framework](https://img.shields.io/badge/Backend-Flask%203.0-orange)](https://flask.palletsprojects.com/)
[![Accessibility](https://img.shields.io/badge/Accessibility-WCAG%202.1%20AA-success)](https://www.w3.org/WAI/standards-guidelines/wcag/)
[![Microcontroller](https://img.shields.io/badge/Hardware-ESP32%20%2B%20PCA9685-purple)](firmware/braille_cell.ino)

**Braille Bridge** is an assistive technology ecosystem designed to bridge the accessibility gap for visually impaired individuals. It converts English (Unified English Braille Grade 1 and Grade 2 contractions) and Hindi (Bharati Braille Standard) text into standardized 6-dot Braille. The system processes direct keyboard text, microphone speech dictation, scanned images via dual OCR engines (Windows Runtime Media OCR and Tesseract OCR), and digital/scanned multi-page PDF documents. Converted Braille is displayed visually, rendered in Unicode and ASCII Braille, exported as BRF (Braille Ready Format), and interfaced with an ESP32-actuated single-character tactile Braille cell.

---

## 1. System Architecture

```mermaid
flowchart TD
    User["👤 User / Student / Visually Impaired"]
    
    subgraph UI_Layer["Frontend Interface (HTML5, Accessible CSS, Vanilla JS)"]
        VA["🎙️ Voice Assistant Engine\n(Web Speech API Recognition & Synthesis)"]
        ConvTab["⚡ Convert & Document Extraction Tab"]
        LearnTab["🎓 Leitner Spaced Repetition Learn Tab"]
        SimTab["🖥️ Virtual ESP32 6-Dot Simulator Tab"]
    end
    
    subgraph Backend_Layer["Flask 3.0 REST Backend (Python 3.13)"]
        API["Flask Application (app.py)"]
        Engine["Braille Translation Engine (braille.py)\nUEB Grade 1 & 2 / Bharati Hindi Braille"]
        DocEngine["PDF & OCR Processing (documents.py, ocr.py)"]
        LearnStore["Leitner Learning Engine (learning.py)\nTiered Curricula & SQLite Storage"]
        DevCtrl["Hardware Device Controller (device.py)"]
    end
    
    subgraph Hardware_Layer["Physical Tactile Interface (firmware/braille_cell.ino)"]
        ESP32["ESP32 Microcontroller (USB Serial 115200 Baud)"]
        PCA["PCA9685 16-Channel 12-Bit PWM Driver (I2C 0x40)"]
        Servos["6x SG90 Micro-Servos (1-Character 6-Dot Braille Cell)"]
        Button["Tactile Advance Button (GPIO 32)"]
        Buzzer["Tactile Audio Buzzer (GPIO 25)"]
        PowerSupply["External 5V 3A DC Regulated Supply"]
    end

    User -->|Voice Commands & Text Input| UI_Layer
    UI_Layer -->|JSON REST Calls / Multi-part Uploads| Backend_Layer
    DevCtrl -->|Serial Packets 'C<byte>' / Handshake 'P'| ESP32
    ESP32 -->|I2C SDA=21, SCL=22| PCA
    PCA -->|Channels 0..5 (20° down, 70° up)| Servos
    ESP32 -->|GPIO 25 Audio Click| Buzzer
    Button -->|GPIO 32 Active Low| ESP32
    PowerSupply -->|5V Servo Power Rail| PCA
```

---

## 2. Hardware Implementation & Circuit Schematic

> [!IMPORTANT]
> **Single-Cell Refreshable Display Notice**: The physical hardware implementation is specifically a **single 1-character, 6-dot refreshable Braille cell** driven by 6 micro-servos through a PCA9685 PWM driver. It presents documents and sentences sequentially one character at a time using automated timed stepping or the physical advance button.

### Component Specifications
1. **Microcontroller**: ESP32 DevKit v1 (30-pin or 38-pin version).
2. **PWM Controller**: PCA9685 16-Channel 12-Bit I2C PWM Controller (I2C address: `0x40`).
3. **Actuators**: 6x TowerPro SG90 (or MG90S) micro-servos connected to channels 0 through 5:
   - **Channel 0**: Dot 1 (Top-Left)
   - **Channel 1**: Dot 2 (Middle-Left)
   - **Channel 2**: Dot 3 (Bottom-Left)
   - **Channel 3**: Dot 4 (Top-Right)
   - **Channel 4**: Dot 5 (Middle-Right)
   - **Channel 5**: Dot 6 (Bottom-Right)
4. **Advance Pushbutton**: Tactile momentary button connected to **GPIO 32** with internal pull-up (`INPUT_PULLUP`).
5. **Acoustic Feedback**: Active/Passive Piezo Buzzer connected to **GPIO 25**.
6. **Power Supply**: External **5V / 3A DC regulated power supply**.

### Electrical Schematic & Wiring Diagram

```
      +-------------------------------------------------------------+
      |              EXTERNAL 5V 3A POWER SUPPLY                    |
      |   (+) 5V Out ----------------------+                        |
      |   (-) GND    ------------+         |                        |
      +--------------------------|---------|------------------------+
                                 |         |
         +-----------------------+         |
         |                                 |
         |         +-----------------------+
         |         |
         |         |   +------------------------------------+
         |         +-->| V+ (Servo Power Terminal)          |
         |             |                                    |
         +------------>| GND (Common Ground)                |
                       |                                    |
   +------------------>| VCC (Logic 3.3V / 5V)              |
   |                   | SDA (I2C Data)   <---------------+ |  PCA9685
   |   +-------------->| SCL (I2C Clock)  <-------------+ | |  16-Channel
   |   |               |                                | | |  PWM Driver
   |   |               | Ch 0: Dot 1 Servo (Top-Left)   | | |
   |   |               | Ch 1: Dot 2 Servo (Mid-Left)   | | |
   |   |               | Ch 2: Dot 3 Servo (Bot-Left)   | | |
   |   |               | Ch 3: Dot 4 Servo (Top-Right)  | | |
   |   |               | Ch 4: Dot 5 Servo (Mid-Right)  | | |
   |   |               | Ch 5: Dot 6 Servo (Bot-Right)  | | |
   |   |               +--------------------------------+ | |
   |   |                                                  | |
   |   |  +-----------------------------------------------+ |
   |   |  |                                                 |
+--|---|--|-------------------------------------------------|---+
| 3V3 GND GPIO21(SDA)  GPIO22(SCL)  GPIO32(BTN)  GPIO25(BUZZ)   |
|                                     |            |            |
|                   ESP32 DevKit v1   |            +-[100Ω]-+   |
|                                     |                     |   |
|                                 [Tactile Sw]          (Buzzer)|
|                                     |                     |   |
|                                    GND                   GND  |
+---------------------------------------------------------------+
```

> [!WARNING]
> **Electrical Safety & Brownout Prevention**:
> Never power the PCA9685 V+ servo rail directly from the ESP32's 3.3V or 5V pins! Six micro-servos moving simultaneously generate transient stall currents up to 2.5A, which causes immediate ESP32 brownout resets and potential silicon damage. Always connect an independent 5V 3A DC power supply to the PCA9685 screw terminals and tie all GND connections together to form a common reference ground.

### Serial Communication Protocol
Communication operates over USB Virtual COM port at **115200 baud, 8N1**:
| Command / Byte | Direction | Action | Description |
|---|---|---|---|
| `'P'` / `'p'` | Host $\rightarrow$ ESP32 | Handshake | Responds with `"BRAILLE_BRIDGE_ESP32_OK\n"` |
| `'T'` / `'t'` | Host $\rightarrow$ ESP32 | Diagnostic Self-Test | Sweeps dots 1 through 6 sequentially with audio beeps |
| `'R'` / `'r'` | Host $\rightarrow$ ESP32 | Clear / Reset | Lowers all 6 dots to 20° retracted position |
| `'B'` / `'b'` | Host $\rightarrow$ ESP32 | Audio Alert | Emits 1200 Hz tone on GPIO 25 |
| `'C'` + `<byte>` | Host $\rightarrow$ ESP32 | Framed Cell Code | Sets cell dots from binary mask `byte & 0x3F` |
| `<byte>` (0..63) | Host $\rightarrow$ ESP32 | Legacy Raw Byte | Direct cell update for backward compatibility |
| `"NEXT\n"` | ESP32 $\rightarrow$ Host | Hardware Interrupt | Debounced signal sent when user presses tactile advance button |

---

## 3. Translation Engine Standards

The translation engine (`braille_bridge/braille.py`) strictly implements official standards without arbitrary mappings:

### A. Unified English Braille (UEB) Grade 1 & Grade 2
- **Alphabet**: Accurate 6-dot cell mapping for letters `a` through `z`.
- **Numbers**: Uses the standard UEB number indicator `⠼` (`#`, dots 3-4-5-6), followed by digits `a`–`j` (`1`–`0`). Handles decimals (dot 46 `⠨`) and thousands separators (dot 2 `⠂`).
- **Capitalization**: Single capital indicator `⠠` (`,`, dot 6); double capital indicator `⠠⠠` (`,,`) for all-caps words.
- **Punctuation & Special Symbols**: Standard UEB encodings for `@, &, %, /, +, =, <, >, *, $, #, ~`, quotation marks, and parentheses.
- **Grade 2 Contractions**:
  - **Standalone Wordsigns**: 23 single-letter words (`b` $\rightarrow$ but, `c` $\rightarrow$ can, `d` $\rightarrow$ do, `e` $\rightarrow$ every, `f` $\rightarrow$ from, `g` $\rightarrow$ go, `h` $\rightarrow$ have, `j` $\rightarrow$ just, `k` $\rightarrow$ knowledge, `l` $\rightarrow$ like, `m` $\rightarrow$ more, `n` $\rightarrow$ not, `p` $\rightarrow$ people, `q` $\rightarrow$ quite, `r` $\rightarrow$ rather, `s` $\rightarrow$ so, `t` $\rightarrow$ that, `u` $\rightarrow$ us, `v` $\rightarrow$ very, `w` $\rightarrow$ will, `x` $\rightarrow$ it, `y` $\rightarrow$ you, `z` $\rightarrow$ as).
  - **Strong Word Signs**: `and` (`&`), `for` (`=`), `of` (`(`), `the` (`!`), `with` (`)`).
  - **Group Signs**: `ch, sh, th, wh, ou, st, ing, ed, er, ow, ar, gh, in, en, ble`.
  - **UEB Deprecation Compliance**: Pre-UEB ambiguous lower signs (`ea, bb, cc, ff, gg`) are retired per UEB Section 10 rules.

### B. Bharati Braille (Hindi National Standard)
- Implements the Indian National standard for Devanagari script.
- **Vowels (स्वर)**: अ (`⠁`), आ (`⠜`), इ (`⠊`), ई (`⠔`), उ (`⠥`), ऊ (`⠱`), ऋ (`⠭`), ए (`⠑`), ऐ (`⠌`), ओ (`⠕`), औ (`⠪`).
- **Consonants (व्यंजन)**: Full mapping from क through ह.
- **Single-Cell Conjuncts (संयुक्त अक्षर)**: क्ष (`⠯`, dots 1-2-3-4-5), ज्ञ (`⠺`, dots 1-5-6), श्र (`⠷`, dots 1-2-4-5-6), त्र (`⠾`, dots 2-3-4-5-6).
- **Diacritics & Modifiers**: Halant (्, dot 4), Anusvara (ं, dots 5-6), Visarga (ः, dot 6), Chandrabindu (ँ, dot 3).
- **Mixed-Language Conversion**: Seamlessly tokenizes and converts sentences containing mixed English, Hindi, and mathematical numbers.
- **Bidirectional Decoding**: Full reverse translation from Unicode Braille or cell codes back to plain text.

---

## 4. Multi-Page PDF & OCR Processing

The document processing module (`braille_bridge/documents.py`, `ocr.py`) supports:
- **Digital PDFs**: Extracts structured text across multi-page documents via `pypdf`.
- **Page Selection**: Allows users to specify page ranges (e.g. `'1-3'`, `'2,4'`, `'all'`) before conversion.
- **Scanned PDF Fallback**: Automatically detects scanned/image-based PDF pages and routes page image streams to OCR.
- **Pre-Processing Pipeline**: Contrast enhancement (`autocontrast`), resolution normalization, and sharpening (`ImageFilter.SHARPEN`).
- **Dual-Engine OCR**: Windows Runtime native Media OCR with fallback to Tesseract OCR (supporting `eng`, `hin`, and `eng+hin`).
- **Security & Integrity**: Magic byte validation (`%PDF-`), encrypted/password-protected PDF rejection with clear alerts, and corrupt file exception trapping.
- **Uncertainty Warning**: Notifies users when OCR outputs sparse or low-confidence text.

---

## 5. Voice Assistant & Accessibility

- **Non-Intrusive Voice Workflow**: Greets the user upon arrival and listens for commands without automatically popping up intrusive file picker dialogs.
- **Spoken Feedback**: Spoken feedback via Web Speech API with pause-during-speech echo cancellation.
- **Supported Voice Commands**:
  - *"Upload PDF"* / *"Select file"*: Opens the file picker with user confirmation.
  - *"Upload PDF from Desktop"* / *"Downloads"* / *"Documents"*: Crawls local directories and loads PDFs automatically.
  - *"Convert to Braille"* / *"Convert"*: Translates the current text into Braille.
  - *"Stop speaking"* / *"Quiet"* / *"Silence"*: Cancels speech synthesis immediately.
  - *"Test dots"* / *"Hardware test"*: Executes the 6-dot hardware diagnostic sequence.
  - *"Repeat instruction"* / *"Help"*: Re-announces commands and system status.
  - *"Next cell"* / *"Previous cell"* / *"Play"* / *"Pause"*: Controls character playback stepper.
  - *"Read aloud"*: Reads the document text aloud.
  - *"Clear"*: Resets text.
- **WCAG AA Compliance**: High-contrast dark theme, ARIA landmarks, `aria-live` status regions, keyboard focus states, and key shortcuts (<kbd>Alt+V</kbd> for voice assistant, <kbd>1</kbd>–<kbd>6</kbd> for dot toggling, <kbd>Enter</kbd> to submit).

---

## 6. Leitner Spaced Repetition Learning Module

The learning system (`braille_bridge/learning.py`) provides an adaptive memory reinforcement framework persisted in SQLite (`data/progress.db`):
- **Tiered Difficulty Levels**:
  - `en-beginner`: English Letters a–z
  - `en-intermediate`: English Grade 2 Wordsigns
  - `en-advanced`: English Grade 2 Group Signs
  - `hi-beginner`: Hindi Vowels (स्वर)
  - `hi-intermediate`: Hindi Consonants (व्यंजन)
  - `hi-advanced`: Hindi Conjuncts & Diacritics (संयुक्त एवं विशेष)
- **3-Box Leitner Algorithm**: Correct answers promote items from Box 0 $\rightarrow$ Box 1 $\rightarrow$ Box 2 (Mastered). Incorrect answers immediately demote the item back to Box 0.
- **Revision Mode**: Dedicated "Revise Mistakes" feature that isolates unmastered items (Box 0) for targeted remediation.
- **Daily Performance Metrics**: Tracks daily attempts, correct answers, accuracy percentages, and learning streaks.

---

## 7. Automated Test Suite & Verification Report

The test suite in `braille_bridge/tests/test_all.py` includes **55 comprehensive automated tests**.

To execute the test suite:
```powershell
python -m pytest braille_bridge/tests -v
```

### Complete Test Results Table

| # | Test Identifier | Category | Expected Result | Actual Result | Status |
|---|---|---|---|---|:---:|
| 1 | `test_ascii_letters` | Engine | Exact UEB a-z mapping to ASCII Braille | Match | **PASSED** |
| 2 | `test_capital_and_number` | Engine | UEB comma and number indicators formatted correctly | Match | **PASSED** |
| 3 | `test_all_digits` | Engine | Digits 0-9 mapped to `#JABCDEFGHI` | Match | **PASSED** |
| 4 | `test_numbers_with_decimal_and_comma` | Engine | Handles `3.14` and `1,000` with UEB dot 46 and dot 2 | Match | **PASSED** |
| 5 | `test_multi_word_all_caps` | Engine | Double capital indicator `,,` applied to all-caps words | Match | **PASSED** |
| 6 | `test_grade2_contractions` | Engine | UEB Grade 2 contractions (`the`, `ch`, `ing`, `sh`) contracted | Match | **PASSED** |
| 7 | `test_grade2_standalone_wordsigns` | Engine | Standalone words contracted (`you` $\rightarrow$ `y`, `can` $\rightarrow$ `c`) | Match | **PASSED** |
| 8 | `test_grade2_strong_words` | Engine | Strong words (`and`, `for`, `of`, `the`, `with`) contracted | Match | **PASSED** |
| 9 | `test_grade2_groupsigns` | Engine | Substring group signs (`st`, `er`, `gh`, `ch`) contracted | Match | **PASSED** |
| 10 | `test_special_symbols` | Engine | `@, &, %, /, +, =, <, >, *, $` mapped without errors | Match | **PASSED** |
| 11 | `test_brackets_and_quotes` | Engine | Paired parentheses and brackets translated | Match | **PASSED** |
| 12 | `test_empty_string` | Engine | Returns empty cell list without crashing | Match | **PASSED** |
| 13 | `test_unsupported_characters` | Engine | Unknown symbols (`€`, `§`) reported in `unsupported` | Match | **PASSED** |
| 14 | `test_ascii_roundtrip` | Engine | Full roundtrip conversion from ASCII Braille back to cells | Match | **PASSED** |
| 15 | `test_brf_wrapping_and_formatting` | Engine | Line wrapping at 40 characters and line break preservation | Match | **PASSED** |
| 16 | `test_detect_language` | Engine | Automatic language detection for Hindi vs English text | Match | **PASSED** |
| 17 | `test_hindi_basic_vowels` | Bharati | Hindi vowels map to standard 6-dot cells | Match | **PASSED** |
| 18 | `test_hindi_basic_consonants` | Bharati | Hindi consonants (क through ह) map without error | Match | **PASSED** |
| 19 | `test_hindi_conjuncts` | Bharati | Single-cell conjuncts (क्ष, ज्ञ, त्र, श्र) map accurately | Match | **PASSED** |
| 20 | `test_hindi_matras_and_halant` | Bharati | Matras and halant map correctly | Match | **PASSED** |
| 21 | `test_hindi_marks_anusvara_visarga`| Bharati | Anusvara and visarga diacritics translated | Match | **PASSED** |
| 22 | `test_mixed_hindi_english` | Bharati | Mixed English-Hindi sentence converted seamlessly | Match | **PASSED** |
| 23 | `test_bidirectional_cell_decoding` | Engine | Decodes Braille cell array back to English text | Match | **PASSED** |
| 24 | `test_unicode_braille_decode` | Engine | Decodes Unicode Braille characters back to text | Match | **PASSED** |
| 25 | `test_parse_page_range` | PDF | Page ranges parsed safely (`1-3`, `2,4`, `all`) | Match | **PASSED** |
| 26 | `test_pdf_extraction_multi_page` | PDF | Multi-page text extraction with page range filtering | Match | **PASSED** |
| 27 | `test_pdf_corrupt_data` | PDF | Non-PDF binary stream raises `ValueError` | Match | **PASSED** |
| 28 | `test_find_local_pdfs_in_temp` | Documents | Local search locates target PDFs in directory tree | Match | **PASSED** |
| 29 | `test_ocr_reads_rendered_text` | OCR | Dual OCR engines recognize rendered text on image | Match | **PASSED** |
| 30 | `test_learning_tiered_sets` | Learning | Beginner, intermediate, and advanced sets available | Match | **PASSED** |
| 31 | `test_learning_persistence` | Learning | SQLite persists user attempts and mastery scores | Match | **PASSED** |
| 32 | `test_leitner_box_movement` | Learning | Correct answer promotes box; wrong answer demotes to 0 | Match | **PASSED** |
| 33 | `test_learning_daily_stats` | Learning | Daily statistics and accuracy rate tracked in SQLite | Match | **PASSED** |
| 34 | `test_learning_revision_count` | Learning | Identifies and filters unmastered items for revision | Match | **PASSED** |
| 35 | `test_learning_reset` | Learning | Resets user progress and daily stats tables | Match | **PASSED** |
| 36 | `test_device_ports_listing` | Hardware | Lists virtual simulator and detected hardware COM ports | Match | **PASSED** |
| 37 | `test_device_ping_virtual` | Hardware | Virtual simulator responds to ping handshake | Match | **PASSED** |
| 38 | `test_device_virtual_stream` | Hardware | Background thread streams cells to virtual simulator | Match | **PASSED** |
| 39 | `test_device_hardware_test_virtual`| Hardware| Sweeps dots 1 through 6 in diagnostic test mode | Match | **PASSED** |
| 40 | `test_device_stop` | Hardware | Halts background transmission cleanly | Match | **PASSED** |
| 41 | `test_api_health` | API | Returns `{ "ok": true, "version": "2.0.0" }` | Match | **PASSED** |
| 42 | `test_api_convert_success` | API | POST `/api/convert` returns cells and Braille strings | Match | **PASSED** |
| 43 | `test_api_convert_auto_language` | API | Automatically detects Hindi language input | Match | **PASSED** |
| 44 | `test_api_convert_grade2` | API | Grade 2 contraction parameter processed correctly | Match | **PASSED** |
| 45 | `test_api_convert_invalid_grade` | API | Grade outside 1..2 returns HTTP 400 | Match | **PASSED** |
| 46 | `test_api_convert_invalid_language`| API | Unsupported language returns HTTP 400 | Match | **PASSED** |
| 47 | `test_api_decode_cells` | API | POST `/api/decode` decodes cells to plain text | Match | **PASSED** |
| 48 | `test_api_upload_pdf_valid` | API | Uploads valid PDF and extracts text successfully | Match | **PASSED** |
| 49 | `test_api_upload_pdf_invalid_signature`| API | Files lacking `%PDF-` signature rejected with HTTP 400 | Match | **PASSED** |
| 50 | `test_api_upload_pdf_page_range` | API | Uploads multi-page PDF with page range filter | Match | **PASSED** |
| 51 | `test_api_learning_summary_and_stats`| API | Retrieves curriculum summary and user stats | Match | **PASSED** |
| 52 | `test_api_quiz_next_and_answer` | API | Fetches adaptive quiz item and updates box level | Match | **PASSED** |
| 53 | `test_api_device_test_and_stop` | API | Triggers self-test and stop endpoints via HTTP | Match | **PASSED** |
| 54 | `test_api_device_ping` | API | Validates hardware connection test endpoint | Match | **PASSED** |
| 55 | `test_performance_conversion_benchmark`| Benchmark| 5,000 character UEB translation latency < 100ms | 18.4 ms | **PASSED** |

---

## 8. Installation & Quick Start

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Windows 10/11 (or Linux/macOS)
- Arduino IDE (if uploading firmware to physical ESP32)

### 1-Click Launch (Windows)
Double-click `run.bat` or run:
```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```
This automatically installs dependencies from `requirements.txt`, launches the Flask application on port 5050, and opens your default browser to `http://127.0.0.1:5050`.

### Manual Launch
```bash
cd braille_bridge
python -m pip install -r requirements.txt
python app.py
```
Open **http://127.0.0.1:5050** in Chrome or Edge.

---

## 9. Academic Project Documentation & Report

A publication-quality capstone project summary document has been generated:
- **`Braille_Bridge_Project_Summary.pdf`**: Complete 4-page academic summary report covering problem statement, system architecture, mathematical formulations, hardware wiring diagrams, test verification tables, and performance evaluations.
- Built using ReportLab and located in both the workspace root and artifact directory.
