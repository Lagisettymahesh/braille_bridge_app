# Braille Bridge: Text-to-Braille Learning, Conversion & Hardware Simulator

An interactive accessibility system built with Flask and JavaScript for learning Braille, converting English & Hindi to Braille, and interfacing with a 6-servo ESP32 Braille cell (or testing it via the built-in real-time Hardware Simulator).

## Quick Start (1-Click Run)

### Windows
- Double-click **
un.bat** (or run powershell ./run.ps1 in PowerShell).
- This automatically installs required dependencies, opens **http://127.0.0.1:5050** in your browser, and starts the local server.

### Manual Launch
`ash
cd braille_bridge
python -m pip install -r requirements.txt
python app.py
`
Then visit **http://127.0.0.1:5050**.

---

## Key Features

1. **Convert Tab**:
   - **Bilingual Support**: English (Grade 1 & Grade 2 UEB contractions) and Hindi (Bharati Braille).
   - **Multiple Inputs**: Direct text typing, speech dictation (Chrome/Edge), or photographing a page (OCR).
   - **Native OCR**: Works out of the box using Windows native OCR engine or Tesseract.
   - **Braille to Text Decoder**: Paste or enter Unicode Braille (e.g., ⠓⠑⠇⠇⠕) or ASCII Braille to decode back to text.
   - **Exports & Speech**: Copy Unicode Braille, download .brf / .txt, or read text aloud via Web Speech API.
   - **Tactile Cell Stepper**: Step through each Braille cell one by one on-screen with adjustable playback speed.

2. **Learn Tab**:
   - **Adaptive Practice**: Leitner spaced repetition boxes persisted in SQLite (data/progress.db).
   - **Read Mode**: See the Braille cell, identify the character among multiple choices.
   - **Write Mode**: See the character and set the dots using mouse clicks or keyboard keys 1–6 and Enter.
   - **Progress Tracking**: Tracks mastery percentage, total attempts, and accuracy per lesson.

3. **Device Tab (Hardware & Simulator)**:
   - **Virtual ESP32 Simulator**: Full on-screen simulation of the ESP32 + PCA9685 6-servo Braille cell.
   - **Real-Time Mechanical Animation**: Staggered 40ms actuation matching firmware logic, showing tactile pins raising (ANGLE_UP = 70°) and lowering (ANGLE_DOWN = 20°).
   - **Audio Feedback**: Realistic 1000 Hz buzzer tone mimicking 	one(BUZZER, 1000, 60) from the ESP32 firmware.
   - **Hardware Next Button**: Interactive Pin 32 button to advance cells.
   - **Physical Hardware**: Ready to connect an ESP32 over USB at 115200 baud running irmware/braille_cell.ino.

---

## Automated Tests

Run the test suite with:
`ash
python -m pytest braille_bridge/tests
`
All 20 unit and integration tests verify the conversion engine, Leitner box learning store, dual OCR engine, bidirectional decoding, and virtual hardware transmission.
