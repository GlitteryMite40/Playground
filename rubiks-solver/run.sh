#!/usr/bin/env bash
# run.sh  –  Start the 4x4 Rubik's Cube Solver (backend + frontend)
# Usage:   bash run.sh
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

info()    { echo -e "${GREEN}[run.sh]${NC} $*"; }
warning() { echo -e "${YELLOW}[run.sh]${NC} $*"; }
error()   { echo -e "${RED}[run.sh]${NC} $*" >&2; }

# ── Check prerequisites ───────────────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || { error "python3 not found"; exit 1; }
command -v node    >/dev/null 2>&1 || { error "node not found"; exit 1; }
command -v npm     >/dev/null 2>&1 || { error "npm not found"; exit 1; }
command -v git     >/dev/null 2>&1 || { error "git not found"; exit 1; }

# ── Backend setup ─────────────────────────────────────────────────────────────
# NOTE: The solver requires Python 3.11.  It pins setuptools==49.2.0 which
# breaks on Python 3.12+.  Create the venv with python3.11 explicitly.
# The solver is Linux-oriented: it uses wget and gunzip to download lookup
# tables from S3, and builds C extensions.  On Windows, use WSL2 or Docker
# (see backend/Dockerfile + docker-compose.yml).
info "Setting up Python 3.11 virtual environment…"
cd "$BACKEND"

if [ ! -d ".venv" ]; then
    python3.11 -m venv .venv || { error "python3.11 not found – install it first"; exit 1; }
    info "Created .venv (Python 3.11)"
fi

source .venv/bin/activate

info "Installing Python dependencies…"
pip install --quiet -r requirements.txt

# Install the NxNxN solver from a git clone (pip install from git URL does not
# support --no-build-isolation, which is required for the pinned setuptools).
if ! python3 -c "import rubikscubennnsolver" 2>/dev/null; then
    info "Cloning rubiks-cube-NxNxN-solver…"
    SOLVER_DIR="$ROOT/rubiks-cube-NxNxN-solver"
    if [ ! -d "$SOLVER_DIR" ]; then
        git clone --depth 1 \
            https://github.com/dwalton76/rubiks-cube-NxNxN-solver \
            "$SOLVER_DIR"
    fi
    info "Installing solver (--no-build-isolation)…"
    pip install --quiet --no-build-isolation "$SOLVER_DIR"
    info "Solver installed ✓"
else
    info "rubikscubennnsolver already installed ✓"
fi

# ── Frontend setup ────────────────────────────────────────────────────────────
info "Installing frontend npm packages…"
cd "$FRONTEND"
npm install --silent

# ── Launch both servers ───────────────────────────────────────────────────────
info "Starting FastAPI backend on http://localhost:8000 …"
cd "$BACKEND"
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

info "Starting Vite frontend on http://localhost:5173 …"
cd "$FRONTEND"
npm run dev &
FRONTEND_PID=$!

# ── Wait / cleanup ────────────────────────────────────────────────────────────
info "Both servers running. Press Ctrl+C to stop."
info "  Frontend: http://localhost:5173"
info "  Backend:  http://localhost:8000/docs"
info ""
warning "FIRST RUN NOTE: The solver downloads lookup tables (sizes vary;"
warning "the first run may fetch several hundred MB) to"
warning "~/.rubiks-cube-lookup-tables/ on the first /solve request."
warning "This can take several minutes. Subsequent solves are fast (<10 s)."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait $BACKEND_PID $FRONTEND_PID
