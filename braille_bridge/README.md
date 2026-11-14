# Braille Bridge: Text-to-Braille Learning and Conversion System

A local web app (Flask + plain JavaScript) with three tabs:

- **Convert**: English (Grade 1 and a Grade 2 subset) and Hindi (Bharati Braille) to Braille. Type, dictate (Chrome/Edge), or photograph a page (OCR). Copy Unicode Braille, download `.brf` / `.txt`, read aloud, step through cells on screen.
- **Learn**: read mode (see the cell, pick the character) and write mode (set the dots with the mouse or keys 1-6). Progress is saved per user in SQLite using Leitner boxes.
- **Device**: send cells to the ESP32 + PCA9685 + 6 servo Braille cell over USB serial.

## Run

Windows: double-click `run.bat`. Mac/Linux: `./run.sh`. Then open http://127.0.0.1:5050.
Manual: `pip install -r requirements.txt` then `python app.py`.

## OCR (optional)

Install Tesseract and the Hindi data.
- Windows: UB-Mannheim installer, tick "Hindi" under additional language data.
- Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-hin`
- macOS: `brew install tesseract tesseract-lang`

Without it everything else still works; the upload control is disabled.

## Hardware (optional)

Flash `firmware/braille_cell.ino` to an ESP32 (Arduino IDE; libraries: Adafruit PWM Servo Driver). Servos 0-5 on PCA9685 channels map to dots 1-6. The app sends one byte per cell (bit n-1 = dot n) at 115200 baud. Pick the port on the Device tab. Without pyserial or a board the on-screen cell still works. The firmware has not been tested on real hardware yet: calibrate servo angles first.

## Tests

`python -m pytest tests` (the OCR test is skipped if Tesseract is missing).

## Limits

- Grade 2 covers a subset of UEB (word signs, 5 strong contractions, 12 group signs).
- Hindi mappings should be checked by a Braille expert before real use.
- OCR output must be proof-read; Hindi OCR accuracy depends on image quality.

## Layout

`app.py` API | `braille.py` engine | `learning.py` progress | `ocr.py` | `device.py` | `static/` UI | `firmware/` | `tests/`
