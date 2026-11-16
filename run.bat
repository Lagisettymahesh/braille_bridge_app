@echo off
cd /d %~dp0braille_bridge
title Braille Bridge
echo ========================================
echo   Starting Braille Bridge...
echo   Voice Assistant + PDF Support Active
echo ========================================

python -m pip install -q -r requirements.txt
echo Server starting at http://127.0.0.1:5050
start http://127.0.0.1:5050
python app.py
pause
