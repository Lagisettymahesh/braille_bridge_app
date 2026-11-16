Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  Starting Braille Bridge...' -ForegroundColor Cyan
Write-Host '  Voice Assistant + PDF Support Active' -ForegroundColor Green
Write-Host '========================================' -ForegroundColor Cyan

python -m pip install -q -r requirements.txt
Start-Process 'http://127.0.0.1:5050'
python app.py
