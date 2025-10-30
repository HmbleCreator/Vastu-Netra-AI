#!/usr/bin/env bash
# Start the Python FastAPI backend (UNIX)
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000