@echo off
echo ============================================================
echo   Starting Backend (FastAPI) on http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Keep this window open while using the app!
echo ============================================================
echo.
cd backend
call venv\Scripts\activate
set PYTHONPATH=%CD%
uvicorn main:app --reload --port 8000
pause
