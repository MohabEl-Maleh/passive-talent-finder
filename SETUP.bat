@echo off
echo ============================================================
echo   Passive Talent Finder - First Time Setup
echo ============================================================
echo.

REM ── Check Python ─────────────────────────────────────────────
echo [1/5] Checking Python...
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo IMPORTANT: Check "Add python.exe to PATH" during installation!
    pause
    exit /b 1
)
python --version
echo Python OK

REM ── Check Node ───────────────────────────────────────────────
echo.
echo [2/5] Checking Node.js...
node --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found.
    echo Please install Node.js LTS from https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo Node.js OK

REM ── Backend venv + packages ───────────────────────────────────
echo.
echo [3/5] Setting up Python backend...
cd backend
python -m venv venv
call venv\Scripts\activate
pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed. Check your internet connection.
    pause
    exit /b 1
)
echo Backend packages installed OK
cd ..

REM ── Frontend packages ─────────────────────────────────────────
echo.
echo [4/5] Installing frontend packages...
cd frontend
call npm install
if errorlevel 1 (
    echo ERROR: npm install failed. Check your internet connection.
    pause
    exit /b 1
)
echo Frontend packages installed OK
cd ..

REM ── Done ──────────────────────────────────────────────────────
echo.
echo [5/5] Setup complete!
echo.
echo ============================================================
echo   NEXT STEPS:
echo   1. Double-click  START_BACKEND.bat   (keep it open)
echo   2. Double-click  START_FRONTEND.bat  (browser opens automatically)
echo   3. Go to http://localhost:3000
echo ============================================================
echo.
pause
