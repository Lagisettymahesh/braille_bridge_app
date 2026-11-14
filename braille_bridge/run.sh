#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
echo "Open http://127.0.0.1:5050 in Chrome or Edge"
python app.py
