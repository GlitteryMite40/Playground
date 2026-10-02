@echo off
REM run.bat  –  Windows launcher for 4x4 Rubik's Cube Solver
REM Usage: run.bat (from the rubiks-solver directory)
REM
REM  *** IMPORTANT: The NxNxN solver is Linux-oriented. ***
REM  It uses wget and gunzip to download lookup tables from S3, and builds
REM  C extensions.  On Windows, run the backend inside WSL2 or Docker instead
REM  (see backend/Dockerfile and docker-compose.yml at the repo root).
REM  This script sets up only the frontend on Windows; run the backend
REM  separately under WSL2 or via: docker compose up backend

SET ROOT=%~dp0
SET BACKEND=%ROOT%backend
SET FRONTEND=%ROOT%frontend

REM ── Backend setup (requires Python 3.11; solver pins setuptools==49.2.0) ────
echo [run.bat] Setting up Python 3.11 virtual environment...
cd /d "%BACKEND%"

IF NOT EXIST ".venv" (
    py -3.11 -m venv .venv 2>NUL || py -m venv .venv 2>NUL || python -m venv .venv
    IF ERRORLEVEL 1 (
        echo [run.bat] ERROR: Python not found. Install it from python.org.
        pause
        exit /b 1
    )
    echo [run.bat] Created .venv
)

CALL .venv\Scripts\activate.bat

echo [run.bat] Installing Python dependencies...
pip install -q -r requirements.txt

python -c "import rubikscubennnsolver" 2>NUL
IF ERRORLEVEL 1 (
    REM Only clone when setup.py is absent – avoids re-cloning a partial or
    REM empty directory left behind by a stale git submodule stub.
    IF NOT EXIST "%ROOT%rubiks-cube-NxNxN-solver\setup.py" (
        echo [run.bat] Cloning rubiks-cube-NxNxN-solver...
        IF EXIST "%ROOT%rubiks-cube-NxNxN-solver" (
            rmdir /s /q "%ROOT%rubiks-cube-NxNxN-solver"
        )
        git clone --depth 1 https://github.com/dwalton76/rubiks-cube-NxNxN-solver "%ROOT%rubiks-cube-NxNxN-solver"
    ) ELSE (
        echo [run.bat] Solver source already present.
    )
    echo [run.bat] Installing solver (--no-build-isolation)...
    pip install -q --no-build-isolation "%ROOT%rubiks-cube-NxNxN-solver"
    echo [run.bat] Solver installed.
)

echo [run.bat] Installing frontend npm packages...
cd /d "%FRONTEND%"
npm install --silent

echo [run.bat] Starting FastAPI backend on http://localhost:8000 ...
cd /d "%BACKEND%"
START "Backend" cmd /k "CALL .venv\Scripts\activate.bat && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo [run.bat] Starting Vite frontend on http://localhost:5173 ...
cd /d "%FRONTEND%"
START "Frontend" cmd /k "npm run dev"

echo.
echo [run.bat] Servers starting. Open http://localhost:5173 in your browser.
echo [run.bat] NOTE: First solve downloads lookup tables (sizes vary; may be
echo [run.bat]       several hundred MB). This can take several minutes.
echo [run.bat] Close the two server windows to stop.
pause
