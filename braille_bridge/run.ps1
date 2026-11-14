Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  Starting Braille Bridge...' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan

Set-Location -Path 
python -m pip install -q -r requirements.txt
Start-Process 'http://127.0.0.1:5050'
python app.py
