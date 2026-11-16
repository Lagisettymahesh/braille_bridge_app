# Braille Bridge: Text-to-Braille Learning, Conversion & Hardware Simulator

An interactive accessibility system built with Flask and JavaScript for learning Braille, converting English & Hindi to Braille, and interfacing with a 6-servo ESP32 Braille cell (or testing it via the built-in real-time Hardware Simulator).

## Quick Start (1-Click Run)

### Windows
- Double-click **run.bat** (or run `powershell ./run.ps1` in PowerShell).
- This automatically installs required dependencies, opens **http://127.0.0.1:5050** in your browser, and starts the local server.

### Voice Assistant Companion
- Run `python voice_assistant.py` to start the hands-free voice assistant.

### Manual Launch
```bash
cd braille_bridge
python -m pip install -r requirements.txt
python app.py
```
Then visit **http://127.0.0.1:5050**.

---

## Key Features

1. **🎙️ Voice Assistant**:
   - **In-Browser Voice Assistant**: Hands-free voice navigation and control directly in the web app. Press <kbd>Alt+V</kbd> or click the Voice Assistant button.
   - **Voice Commands**: Say *"Open website"*, *"Upload PDF"*, *"Convert"*, *"Read aloud"*, *"Open learn"*, *"Open device"*, or *"Clear"*.
   - **Interactive Spoken Guidance**: Spoken announcements for visually impaired users using the Web Speech API.
   - **Standalone Companion (`voice_assistant.py`)**: Can be launched from terminal to open the website and upload PDFs hands-free.

2. **📄 Document & PDF Upload**:
   - **Direct PDF Processing**: Upload `.pdf` textbooks, notes, or documents.
   - **Instant Text Extraction & Braille Conversion**: Automatically extracts text using `pypdf` and renders Braille cells with audio feedback.
   - **Page OCR**: Upload images or photos of printed pages with Windows Native OCR or Tesseract.

3. **Convert Tab**:
   - **Bilingual Support**: English (Grade 1 & Grade 2 UEB contractions) and Hindi (Bharati Braille).
   - **Multiple Inputs**: Direct text typing, speech dictation (Chrome/Edge), PDF document upload, or photographing a page (OCR).
   - **Native OCR**: Works out of the box using Windows native OCR engine or Tesseract.
   - **Braille to Text Decoder**: Paste or enter Unicode Braille (e.g., ⠓⠑⠇⠇⠕) or ASCII Braille to decode back to text.
   - **Exports & Speech**: Copy Unicode Braille, download .brf / .txt, or read text aloud via Web Speech API.
   - **Tactile Cell Stepper**: Step through each Braille cell one by one on-screen with adjustable playback speed.

4. **Learn Tab**:
   - **Adaptive Practice**: Leitner spaced repetition boxes persisted in SQLite (`data/progress.db`).
   - **Read Mode**: See the Braille cell, identify the character among multiple choices.
   - **Write Mode**: See the character and set the dots using mouse clicks or keyboard keys 1–6 and Enter.
   - **Progress Tracking**: Tracks mastery percentage, total attempts, and accuracy per lesson.

5. **Device Tab (Hardware & Simulator)**:
   - **Virtual ESP32 Simulator**: Full on-screen simulation of the ESP32 + PCA9685 6-servo Braille cell.
   - **Real-Time Mechanical Animation**: Staggered 40ms actuation matching firmware logic, showing tactile pins raising (ANGLE_UP = 70°) and lowering (ANGLE_DOWN = 20°).
   - **Audio Feedback**: Realistic 1000 Hz buzzer tone mimicking `tone(BUZZER, 1000, 60)` from the ESP32 firmware.
   - **Hardware Next Button**: Interactive Pin 32 button to advance cells.
   - **Physical Hardware**: Ready to connect an ESP32 over USB at 115200 baud running `firmware/braille_cell.ino`.

---

## Automated Tests

Run the test suite with:
```bash
python -m pytest braille_bridge/tests
```
All 23 unit and integration tests verify the conversion engine, PDF extraction, Leitner box learning store, dual OCR engine, bidirectional decoding, and virtual hardware transmission.
