"""
4x4 Rubik's Cube Solver – FastAPI backend
==========================================
Endpoints:
  POST /solve   – validate & solve a 96-sticker state
  GET  /demo    – return a scrambled cube state
  GET  /health  – liveness probe

Solver: rubiks-cube-NxNxN-solver by dwalton76
  git clone https://github.com/dwalton76/rubiks-cube-NxNxN-solver
  pip install --no-build-isolation ./rubiks-cube-NxNxN-solver  (Python 3.11 venv)

State format (both request and response):
  96-element list of single-char color codes in ULFRBD face order (16 per face).
  Color codes: U=W, D=Y, F=G, B=B, R=R, L=O
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List

BACKEND_DIR = str(Path(__file__).parent.resolve())
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

SCRIPTS_DIR = str(Path(sys.executable).parent.resolve())
if SCRIPTS_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = SCRIPTS_DIR + os.pathsep + os.environ.get("PATH", "")

def get_subprocess_env(extra: dict | None = None) -> dict:
    env = dict(os.environ)
    curr_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = BACKEND_DIR + (os.pathsep + curr_pp if curr_pp else "")
    if extra:
        env.update(extra)
    return env

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── App & CORS ────────────────────────────────────────────────────────────────
app = FastAPI(title="4x4 Rubik's Cube Solver", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",  # vite preview
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Constants ─────────────────────────────────────────────────────────────────
VALID_COLORS = {"W", "Y", "G", "B", "R", "O"}
FACE_ORDER = ["U", "L", "F", "R", "B", "D"]  # 16 stickers each

# Color code → solver's single-letter face code
# rubikscubennnsolver uses U/L/F/R/B/D as color identifiers on a solved cube
# The 4x4 center pieces define each face color:
#   U=white, D=yellow, F=green, B=blue, R=red, L=orange
COLOR_TO_FACE: dict[str, str] = {
    "W": "U",
    "Y": "D",
    "G": "F",
    "B": "B",
    "R": "R",
    "O": "L",
}

# Solved state (ULFRBD order, 16 stickers each face)
SOLVED_STATE = (
    ["W"] * 16  # U
    + ["O"] * 16  # L
    + ["G"] * 16  # F
    + ["R"] * 16  # R
    + ["B"] * 16  # B
    + ["Y"] * 16  # D
)

# A fixed 30-move demo scramble (WCA notation)
DEMO_SCRAMBLE = (
    "Rw2 U Fw2 Rw' U2 Fw U' Rw U2 Fw' Rw2 U Fw' Rw "
    "U' Fw2 Rw U' Fw' Rw' U Fw Rw2 U' Fw' Rw U2 Fw Rw'"
)


# ── Models ────────────────────────────────────────────────────────────────────
class SolveRequest(BaseModel):
    state: List[str]

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: List[str]) -> List[str]:
        if len(v) != 96:
            raise ValueError(f"Expected 96 stickers, got {len(v)}")
        for i, c in enumerate(v):
            if c not in VALID_COLORS:
                raise ValueError(f"Invalid color '{c}' at position {i}")
        # Check each color appears exactly 16 times
        from collections import Counter
        counts = Counter(v)
        for color in VALID_COLORS:
            if counts[color] != 16:
                raise ValueError(
                    f"Color '{color}' appears {counts[color]} times (expected 16)"
                )
        return v


class SolveResponse(BaseModel):
    solution: str
    moves: List[str]
    message: str = ""


class DemoResponse(BaseModel):
    state: List[str]
    scramble: str


# ── Notation normalisation ────────────────────────────────────────────────────
# rubikscubennnsolver outputs moves like "Rw", "Uw", "Rw'", "Uw2" etc.
# cubing.js/twisty-player understands the same WCA notation so we mainly
# need to ensure consistent formatting (no extra spaces, etc.)
def normalize_move(move: str) -> str:
    """Normalize a single move token so cubing.js accepts it."""
    move = move.strip()
    if not move:
        return ""
    # The solver sometimes emits lowercase variants – canonicalize
    # e.g. "rw" → "Rw", "uw2" → "Uw2"
    # Pattern: optional layer count prefix (2/3) + face letter + optional 'w' + optional modifier (2/')
    m = re.match(r"^(\d+)?([UDFBLRudflbr])(w)?(\d+)?(')?$", move)
    if not m:
        return move  # return as-is if we can't parse it
    prefix, face, wide, num_after, prime = m.groups()
    face = face.upper()
    wide = wide or ""
    modifier = ""
    if prime:
        modifier = "'"
    elif num_after and num_after == "2":
        modifier = "2"
    elif num_after and num_after == "3":
        modifier = "'"  # 3 = same as prime for 4x4
    result = face + wide + modifier
    # prefix digit (e.g. "3Rw") is valid WCA for 4x4, keep it
    if prefix and prefix != "1":
        result = prefix + result
    return result


def normalize_solution(raw: str) -> list[str]:
    """Split raw solver output into a clean list of WCA move tokens."""
    tokens = raw.strip().split()
    moves: list[str] = []
    for t in tokens:
        n = normalize_move(t)
        if n:
            moves.append(n)
    return moves


# ── Solver integration ────────────────────────────────────────────────────────
def state_to_solver_string(state: List[str]) -> str:
    """
    Convert the 96-element color list to the string format expected by
    rubikscubennnsolver's RubiksCube444 class.

    The solver expects a 96-char string where each character is the face
    letter of the color (U/L/F/R/B/D), in ULFRBD order.
    """
    return "".join(COLOR_TO_FACE[c] for c in state)


FACE_TO_COLOR: dict[str, str] = {
    "U": "W",
    "L": "O",
    "F": "G",
    "R": "R",
    "B": "B",
    "D": "Y",
}


def run_solver(state_str: str) -> str:
    """
    Solve the 4x4 Rubik's cube using pure in-memory reduction solver.
    Returns the solution string (space-joined WCA moves).
    """
    from reduction_solver import solve_444
    log.info("Running in-memory reduction solver...")
    moves = solve_444(state_str)
    solution = " ".join(moves)
    log.info("Solver output (%d moves): %s", len(moves), solution[:120])
    return solution


def apply_move_to_state(state: List[str], move: str) -> List[str]:
    """
    Apply a single WCA move to a 96-sticker state list.
    Returns the new state list.
    """
    from rubikscubennnsolver.RubiksCube444 import RubiksCube444
    cube = RubiksCube444(state_to_solver_string(state), "ULFRBD")
    cube.rotate(move)
    return [FACE_TO_COLOR[c] for c in cube.state[1:]]


def apply_moves_verify(initial: List[str], moves: List[str]) -> bool:
    """
    Verify the solution is correct by applying all moves to the initial state
    and checking that the result is solved.
    """
    try:
        from rubikscubennnsolver.RubiksCube444 import RubiksCube444
        cube = RubiksCube444(state_to_solver_string(initial), "ULFRBD")
        for m in moves:
            cube.rotate(m)
        result = [FACE_TO_COLOR[c] for c in cube.state[1:]]
        return result == SOLVED_STATE
    except Exception as exc:
        log.warning("Verification error: %s", exc)
        return False


def apply_scramble(scramble: str) -> List[str]:
    """Apply a scramble string to a solved cube and return the resulting state."""
    from rubikscubennnsolver.RubiksCube444 import RubiksCube444
    cube = RubiksCube444(state_to_solver_string(SOLVED_STATE), "ULFRBD")
    for m in scramble.strip().split():
        cube.rotate(m)
    return [FACE_TO_COLOR[c] for c in cube.state[1:]]


# ── Routes ────────────────────────────────────────────────────────────────────
router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/demo", response_model=DemoResponse)
def demo():
    """Return a scrambled cube state derived from a fixed 30-move scramble."""
    try:
        scrambled = apply_scramble(DEMO_SCRAMBLE)
        return DemoResponse(state=scrambled, scramble=DEMO_SCRAMBLE)
    except Exception as exc:
        log.exception("Demo scramble failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/solve", response_model=SolveResponse)
def solve(req: SolveRequest):
    """
    Validate the cube state, solve it, verify the solution, and return it.
    """
    log.info("Received solve request")

    if req.state == SOLVED_STATE:
        log.info("Cube is already in solved state")
        return SolveResponse(
            solution="",
            moves=[],
            move_count=0,
            verified=True,
        )

    solver_str = state_to_solver_string(req.state)
    log.info("Solver input string (first 48 chars): %s", solver_str[:48])

    try:
        raw_solution = run_solver(solver_str)
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Solver timed out.",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    moves = normalize_solution(raw_solution)
    if not moves:
        if req.state == SOLVED_STATE:
            return SolveResponse(
                solution="",
                moves=[],
                move_count=0,
                verified=True,
            )
        raise HTTPException(status_code=500, detail="Solver returned empty solution")

    solution_str = " ".join(moves)
    log.info("Normalized solution (%d moves): %s", len(moves), solution_str[:120])

    # Verify correctness
    try:
        ok = apply_moves_verify(req.state, moves)
        if not ok:
            log.error("Solution verification FAILED")
            raise HTTPException(
                status_code=500,
                detail="Solution verification failed – the solver returned an incorrect solution.",
            )
        log.info("Solution verified [OK]")
    except HTTPException:
        raise
    except Exception as exc:
        log.warning("Could not verify solution (non-fatal): %s", exc)

    return SolveResponse(
        solution=solution_str,
        moves=moves,
        message=f"Solved in {len(moves)} moves",
    )


# Register routes at both "/api" (for Vercel service rewrite) and root "/" (for direct / local access)
app.include_router(router, prefix="/api")
app.include_router(router)
