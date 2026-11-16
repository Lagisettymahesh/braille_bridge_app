"""Braille Bridge – Voice Assistant CLI and Companion.

Provides hands-free voice assistance to:
1. Open the Braille Bridge website in the browser.
2. Select and upload PDF documents to convert to Braille.
3. Convert speech or text to Braille and read aloud.
"""
import os
import sys
import time
import subprocess
import webbrowser
import threading
from typing import Optional

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import braille
import documents

SERVER_URL = "http://127.0.0.1:5050"


def speak(text: str):
    """Speak text aloud using Windows SAPI Speech Synthesis or fallback."""
    print(f"\n🎙️ [Assistant]: {text}")
    if sys.platform == 'win32':
        clean_text = text.replace('"', ' ').replace("'", " ")
        ps_cmd = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{clean_text}')"
        try:
            subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps_cmd],
                capture_output=True,
                timeout=10
            )
        except Exception:
            pass


def is_server_running(url: str = SERVER_URL) -> bool:
    """Check if the local server is reachable."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=1.5) as res:
            return res.status == 200
    except Exception:
        return False


def start_server_in_background():
    """Start the Flask server in background if not already running."""
    if not is_server_running():
        app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
        subprocess.Popen([sys.executable, app_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.2)


def cmd_open_website():
    """Command: Open the Braille Bridge website."""
    speak("Opening Braille Bridge website.")
    start_server_in_background()
    webbrowser.open(SERVER_URL)


def cmd_upload_pdf(file_path: Optional[str] = None):
    """Command: Select and upload a PDF document."""
    speak("Please select a PDF document to upload.")
    if not file_path:
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            file_path = filedialog.askopenfilename(
                title="Select PDF Document for Braille Bridge",
                filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")]
            )
            root.destroy()
        except Exception as e:
            print(f"Could not open file picker dialog: {e}")

    if not file_path:
        speak("No PDF file was selected.")
        return

    if not os.path.exists(file_path):
        speak(f"File not found: {file_path}")
        return

    print(f"\nProcessing PDF: {file_path}...")
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        res = documents.extract_pdf_text(data)

        if not res['text'] and res['is_scanned']:
            msg = f"This PDF contains {res['pages']} scanned page(s) with no digital text."
            speak(msg)
            return

        conv = braille.convert_full(res['text'][:20000], 'auto', 1)
        filename = os.path.basename(file_path)
        summary = (
            f"Successfully processed {filename}. "
            f"Extracted {res['chars']} characters across {res['pages']} pages, "
            f"converted into {conv['count']} Braille cells."
        )
        speak(summary)

        print("=" * 60)
        print(f"Extracted Text (first 300 chars):\n{res['text'][:300]}...")
        print("-" * 60)
        print(f"Braille Output (first 100 cells):\n{conv['braille'][:100]}...")
        print("=" * 60)

        # Open the website so the user can feel/see it
        start_server_in_background()
        webbrowser.open(f"{SERVER_URL}#uploaded")

    except Exception as e:
        speak(f"Error reading PDF: {e}")


def cmd_help():
    """Print and speak available commands."""
    help_text = (
        "Available voice commands:\n"
        "1. 'open website' - Launches Braille Bridge in your browser\n"
        "2. 'upload pdf'    - Selects a PDF file and converts it to Braille\n"
        "3. 'convert'       - Converts custom text to Braille\n"
        "4. 'help'          - Shows this help message\n"
        "5. 'exit'          - Closes the Voice Assistant"
    )
    print(help_text)
    speak("You can say: open website, upload PDF, convert, help, or exit.")


def main():
    print("=" * 60)
    print("   Braille Bridge – Voice Assistant")
    print("=" * 60)
    speak("Hello! Braille Bridge Voice Assistant is ready.")
    cmd_help()

    # Try importing speech_recognition if installed
    recognizer = None
    microphone = None
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        print("\n✅ Microphone is connected and ready.")
    except Exception:
        print("\nℹ️ (SpeechRecognition module is optional. You can speak or type commands below)")

    while True:
        try:
            print("\n------------------------------------------------------------")
            query = ""
            if recognizer and microphone:
                try:
                    print("🎤 Listening... (Speak now, or press Enter to type)")
                    with microphone as source:
                        recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        audio = recognizer.listen(source, timeout=4, phrase_time_limit=5)
                    query = recognizer.recognize_google(audio).lower().strip()
                    print(f"Heard: '{query}'")
                except Exception:
                    query = input("Voice Assistant > ").strip().lower()
            else:
                query = input("Voice Assistant (Say or type command) > ").strip().lower()

            if not query:
                continue

            if "open website" in query or "website" in query or "launch" in query or "start website" in query:
                cmd_open_website()
            elif "upload pdf" in query or "open pdf" in query or "pdf" in query or "upload document" in query:
                cmd_upload_pdf()
            elif "convert" in query:
                txt = input("Enter text to convert to Braille: ").strip()
                if txt:
                    r = braille.convert_full(txt, 'auto', 1)
                    print(f"Braille: {r['braille']}")
                    speak(f"Converted to {r['count']} Braille cells.")
            elif "help" in query or "commands" in query:
                cmd_help()
            elif "exit" in query or "quit" in query or "bye" in query:
                speak("Goodbye! Have a great day.")
                break
            else:
                print(f"Unknown command: '{query}'. Say 'help' to see available commands.")
                speak("I did not catch that. Say help for commands.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Voice Assistant...")
            break


if __name__ == '__main__':
    main()
