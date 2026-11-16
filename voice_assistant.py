"""Launcher for Braille Bridge Voice Assistant."""
import os
import sys
import subprocess

if __name__ == '__main__':
    target = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'braille_bridge', 'voice_assistant.py')
    sys.exit(subprocess.call([sys.executable, target] + sys.argv[1:]))
