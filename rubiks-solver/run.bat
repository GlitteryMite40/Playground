@echo off
REM run.bat  –  Windows launcher for 4x4 Rubik's Cube Solver
REM Usage: run.bat (from the rubiks-solver directory)

SET ROOT=%~dp0
SET BACKEND=%ROOT%backend
SET FRONTEND=%ROOT%frontend

echo [run.bat] Setting up Python virtual environment...
cd /d "%BACKEND%"

IF NOT EXIST ".venv" (
    python -m venv .venv
    echo [run.bat] Created .venv
)

CALL .venv\Scripts\activate.bat

echo [run.bat] Installing Python dependencies...
pip install -q -r requirements.txt

python -c "import rubikscubennnsolver" 2>NUL
IF ERRORLEVEL 1 (
    echo [run.bat] Installing rubiks-cube-NxNxN-solver...
    pip install -q "git+https://github.com/dwalton76/rubiks-cube-NxNxN-solver.git"
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
echo [run.bat] NOTE: First solve will download ~50MB of lookup tables (2-5 min).
echo [run.bat] Close the two server windows to stop.
pause
