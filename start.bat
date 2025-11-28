@echo off
set PORT=8000
uvicorn main:app --reload --host 127.0.0.1 --port %PORT%
pause
