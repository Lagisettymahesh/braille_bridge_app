"""Braille Bridge – Voice Assistant CLI and Desktop Companion.

Provides hands-free voice assistance to:
1. Open permitted folders (Documents, Downloads, Desktop, Capstone) using voice.
2. Search, list, and read filenames aloud one by one with ordinal numbers.
3. Select files by speaking their name or number ("select the second one", "number two").
4. Confirm upload and automatically extract text, run OCR if scanned, and convert to Braille.
5. Provide 100% blind independence without requiring sighted assistance or clicking buttons.
"""
import os
import sys
import time
import subprocess
import webbrowser
import threading
from typing import Optional, List, Dict, Any

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
                timeout=12
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


class VoiceFileManager:
    """Conversational voice file management state machine for blind users."""

    def __init__(self):
        self.state = 'IDLE'  # 'IDLE' | 'LISTING' | 'AWAITING_CONFIRMATION' | 'PROCESSING'
        self.current_folder = 'documents'
        self.current_subpath = ''
        self.candidates: List[Dict[str, Any]] = []
        self.selected_file: Optional[Dict[str, Any]] = None
        self.page = 1
        self.total_pages = 1
        self.last_spoken = ''

    def browse_folder(self, folder_alias: str = 'documents', subpath: str = '', page: int = 1):
        res = documents.browse_folder(folder_alias, subpath, page=page, page_size=6)
        if not res.get('ok'):
            speak(f"Could not open folder {folder_alias}: {res.get('error')}")
            return

        self.current_folder = res.get('folder_name', folder_alias)
        self.current_subpath = subpath
        self.candidates = res.get('files', [])
        self.page = res.get('page', 1)
        self.total_pages = res.get('total_pages', 1)
        self.state = 'LISTING'
        self.last_spoken = res.get('spoken_summary', '')

        print(f"\n[Folder: {self.current_folder}] (Page {self.page} of {self.total_pages})")
        for f in self.candidates:
            print(f"  [{f['id']}] {f['filename']} ({f['size_str']})")

        speak(self.last_spoken)

    def search(self, query: str, folder_alias: str = ''):
        res = documents.search_files(query, folder_alias, max_results=6)
        self.candidates = res.get('files', [])
        self.page = 1
        self.total_pages = 1
        self.state = 'LISTING'
        self.last_spoken = res.get('spoken_summary', '')

        print(f"\n[Search Results: '{query}']")
        for f in self.candidates:
            print(f"  [{f['id']}] {f['filename']} ({f.get('folder', '')})")

        speak(self.last_spoken)

    def select_candidate(self, phrase: str) -> bool:
        if not self.candidates:
            speak("No files are currently listed. You can say: find my project PDF, or open Documents.")
            return False

        filenames = [f['filename'] for f in self.candidates]
        idx = documents.resolve_ordinal_selection(phrase, len(self.candidates), filenames)

        if idx is None:
            speak(f"I didn't catch that. Please say number 1 through {len(self.candidates)}, or speak the filename.")
            return False

        self.selected_file = self.candidates[idx]
        self.state = 'AWAITING_CONFIRMATION'
        prompt = f"You selected {self.selected_file['filename']}. Shall I upload it?"
        self.last_spoken = prompt
        speak(prompt)
        return True

    def confirm_upload(self):
        if not self.selected_file:
            speak("No file is selected. Please select a file first.")
            return

        target = self.selected_file
        self.state = 'PROCESSING'
        speak(f"Uploading and processing {target['filename']}...")

        try:
            res = documents.process_selected_file(target['path'], lang='auto', grade=1)
            self.state = 'IDLE'
            self.selected_file = None

            print("\n" + "=" * 60)
            print(f"Document: {res['filename']} ({res['pages']} pages, {res['chars']} chars)")
            print(f"Extracted Text:\n{res['text'][:300]}...")
            print("-" * 60)
            if res.get('conversion'):
                print(f"Braille Unicode:\n{res['conversion']['braille'][:150]}...")
                print(f"Braille ASCII:\n{res['conversion']['ascii'][:150]}...")
                print(f"Total Braille Cells: {res['conversion']['count']}")
            print("=" * 60)

            speak(res['spoken_summary'])

            # Open website so the user can interact or feel the cell
            start_server_in_background()
            webbrowser.open(f"{SERVER_URL}#uploaded")

        except Exception as e:
            speak(f"Error processing document: {e}")
            self.state = 'LISTING'

    def cancel(self):
        self.selected_file = None
        speak("Upload cancelled. Which file would you like to select?")
        self.state = 'LISTING' if self.candidates else 'IDLE'

    def repeat(self):
        if self.state == 'AWAITING_CONFIRMATION' and self.selected_file:
            speak(f"You selected {self.selected_file['filename']}. Shall I upload it?")
        elif self.state == 'LISTING' and self.last_spoken:
            speak(self.last_spoken)
        else:
            speak("Welcome to Braille Bridge. Which file would you like to convert? You can say: Find my project PDF, or open Documents, Downloads, or Desktop.")


def cmd_help():
    """Print and speak available commands."""
    help_text = (
        "Available voice commands:\n"
        "1. 'find my project pdf'   - Searches your folders for matching files\n"
        "2. 'open documents'        - Browses your Documents folder and reads files aloud\n"
        "3. 'open downloads'        - Browses your Downloads folder\n"
        "4. 'open desktop'          - Browses your Desktop folder\n"
        "5. 'select the second one' - Selects a file by number or name\n"
        "6. 'yes' / 'confirm'       - Confirms upload and converts to Braille\n"
        "7. 'repeat'                - Repeats available files or instruction\n"
        "8. 'cancel'                - Cancels file selection\n"
        "9. 'convert'               - Converts custom text to Braille\n"
        "10. 'open website'         - Launches Braille Bridge in your browser\n"
        "11. 'exit'                 - Closes the Voice Assistant"
    )
    print(help_text)
    speak("You can say: find my project PDF, open Documents, open Downloads, or help.")


def main():
    print("=" * 60)
    print("   Braille Bridge – Independent Voice Assistant")
    print("=" * 60)

    mgr = VoiceFileManager()
    speak("Hello! Welcome to Braille Bridge. Which file would you like to convert? You can say: find my project PDF, or open Documents, Downloads, or Desktop.")

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
                        recognizer.adjust_for_ambient_noise(source, duration=0.4)
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=6)
                    query = recognizer.recognize_google(audio).lower().strip()
                    print(f"Heard: '{query}'")
                except Exception:
                    query = input("Voice Assistant > ").strip().lower()
            else:
                query = input("Voice Assistant (Say or type command) > ").strip().lower()

            if not query:
                continue

            # 1. Confirmation state handling
            if mgr.state == 'AWAITING_CONFIRMATION':
                if query in ('yes', 'yeah', 'sure', 'confirm', 'upload', 'upload it', 'please do') or 'yes upload' in query:
                    mgr.confirm_upload()
                    continue
                elif query in ('no', 'cancel', 'wrong', 'stop') or 'don t upload' in query:
                    mgr.cancel()
                    continue
                elif 'repeat' in query or 'again' in query:
                    mgr.repeat()
                    continue

            # 2. General Cancel & Repeat
            if query in ('cancel', 'stop') or 'cancel selection' in query:
                mgr.cancel()
                continue
            if 'repeat' in query or 'again' in query:
                mgr.repeat()
                continue

            # 3. Selection in LISTING mode
            if mgr.state == 'LISTING':
                is_sel = any(w in query for w in ['select', 'choose', 'first', 'second', 'third', 'fourth', 'fifth', 'number', '1', '2', '3', 'last'])
                if is_sel:
                    if mgr.select_candidate(query):
                        continue

            # 4. Folder Navigation
            if 'open document' in query or 'documents' in query:
                mgr.browse_folder('documents')
            elif 'open download' in query or 'downloads' in query:
                mgr.browse_folder('downloads')
            elif 'open desktop' in query or 'desktop' in query:
                mgr.browse_folder('desktop')
            elif 'capston' in query:
                mgr.browse_folder('capston')

            # 5. Search Commands
            elif query.startswith('find ') or query.startswith('search ') or 'project pdf' in query or 'find my' in query:
                q_text = query.replace('find my', '').replace('find', '').replace('search for', '').replace('search', '').strip()
                if not q_text or q_text == 'pdf':
                    q_text = 'project'
                mgr.search(q_text)

            elif 'upload' in query or 'pdf' in query:
                speak("Which file would you like to convert? You can say: find my project PDF, or open Documents, Downloads, or Desktop.")

            # 6. Convert Text Directly
            elif 'convert' in query:
                txt = input("Enter text to convert to Braille: ").strip()
                if txt:
                    r = braille.convert_full(txt, 'auto', 1)
                    print(f"Braille Unicode: {r['braille']}")
                    speak(f"Converted to {r['count']} Braille cells.")

            # 7. Website, Help, Exit
            elif 'open website' in query or 'website' in query or 'launch' in query:
                cmd_open_website()
            elif 'help' in query or 'commands' in query:
                cmd_help()
            elif 'exit' in query or 'quit' in query or 'bye' in query:
                speak("Goodbye! Have a great day.")
                break
            else:
                print(f"Unknown command: '{query}'. Say 'help' for available commands.")
                speak("I did not catch that. Say help for commands.")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting Voice Assistant...")
            break


if __name__ == '__main__':
    main()

