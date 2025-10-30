@echo off
REM Start the Python FastAPI backend (Windows)
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause