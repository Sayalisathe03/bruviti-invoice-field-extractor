# Bruviti Invoice Field Extractor PowerShell Launcher
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Starting Bruviti Invoice Field Extractor Service     " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$PythonExe = if (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    "$ScriptDir\.venv\Scripts\python.exe"
} else {
    "python"
}

Write-Host "Using Python: $PythonExe" -ForegroundColor Green
Write-Host "Server URL:   http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the server.`n"

# Open the browser to the UI
Start-Process "http://127.0.0.1:8000"

# Launch the server
& $PythonExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
