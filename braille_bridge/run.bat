@echo off
cd /d %~dp0
title Braille Bridge
echo ========================================
echo   Starting Braille Bridge...
echo ========================================

python -m pip install -q -r requirements.txt
echo Server starting at http://127.0.0.1:5050
start http://127.0.0.1:5050
python app.py
pause

