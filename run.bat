@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   Starting Bruviti Invoice Field Extractor Service
echo ========================================================
echo.

IF EXIST ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) ELSE (
    set "PYTHON_EXE=python"
)

echo Using Python: %PYTHON_EXE%
echo Starting server on http://127.0.0.1:8000 ...
echo Press Ctrl+C in this window to stop the server.
echo.

start "" "http://127.0.0.1:8000"

"%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
