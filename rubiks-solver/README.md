# 4×4 Rubik's Cube Solver

A full-stack web application that lets you paint a scrambled 4×4 cube, solve it
with the **rubiks-cube-NxNxN-solver** library, and animate the solution in an
interactive 3D viewer.

```
rubiks-solver/
├── backend/
│   ├── main.py              # FastAPI app (all endpoints)
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── types/
│       │   └── cube.ts
│       ├── utils/
│       │   ├── cubeUtils.ts
│       │   └── api.ts
│       └── components/
│           ├── StickerEditor.tsx   # 4×4 net, color counters, paint tool
│           └── SolutionViewer.tsx  # twisty-player, move list, playback
├── run.sh      # Linux / macOS launcher
├── run.bat     # Windows launcher
└── README.md
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10 + |
| Node.js | 18 + |
| npm | 9 + |
| git | any |

**Windows** users: ensure Python and Node are on `PATH`.

---

## Quick start (one command)

### Linux / macOS
```bash
cd rubiks-solver
bash run.sh
```

### Windows
```bat
cd rubiks-solver
run.bat
```

Both scripts will:
1. Create a Python virtual environment in `backend/.venv`
2. Install FastAPI, uvicorn, and the NxNxN solver
3. Install npm packages in `frontend/`
4. Start the backend on **http://localhost:8000**
5. Start the frontend on **http://localhost:5173**

Open **http://localhost:5173** in your browser.

---

## Manual setup (step by step)

### 1 – Backend

```bash
cd rubiks-solver/backend

# Create and activate venv
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install FastAPI + uvicorn
pip install -r requirements.txt

# Install the NxNxN cube solver from GitHub
pip install "git+https://github.com/dwalton76/rubiks-cube-NxNxN-solver.git"

# Start the server
uvicorn main:app --reload --port 8000
```

### 2 – Frontend

```bash
cd rubiks-solver/frontend

npm install
npm run dev
```

---

## First-run solver setup

On the **first `/solve` request** the solver will automatically download its
lookup tables (~50 MB) from the internet to:

```
~/.rubiks-cube-lookup-tables/   # Linux / macOS
%USERPROFILE%\.rubiks-cube-lookup-tables\  # Windows
```

This takes **2–5 minutes** depending on your connection. The status banner in
the UI will say "Solving… This may take 1–3 minutes on first run…". Subsequent
solves run in **under 15 seconds**.

You can also pre-download the tables:

```bash
python3 -c "
from rubikscubennnsolver.RubiksCube444 import RubiksCube444
cube = RubiksCube444('UUUUUUUUUUUUUUUULLLLLLLLLLLLLLLLFFFFFFFFFFFFFFFFRRRRRRRRRRRRRRRRBBBBBBBBBBBBBBBBDDDDDDDDDDDDDDDD', 'ULFRBD')
cube.solve()
print('Tables ready!')
"
```

---

## API reference

### `GET /health`
Returns `{"status": "ok"}` if the server is running.

### `GET /demo`
Returns a pre-scrambled cube state.

**Response**
```json
{
  "state": ["W","W",...],   // 96 color codes
  "scramble": "Rw2 U Fw2 …" // the 30-move scramble applied
}
```

### `POST /solve`
Solve a 96-sticker cube state.

**Request body**
```json
{
  "state": ["W","W","W","W","W","W","W","W","W","W","W","W","W","W","W","W",
            "O","O",...,
            "G","G",...,
            "R","R",...,
            "B","B",...,
            "Y","Y",...]
}
```

State order: **U L F R B D** (16 stickers per face, row-major).  
Color codes: `W`=white, `Y`=yellow, `G`=green, `B`=blue, `R`=red, `O`=orange.

**Response**
```json
{
  "solution": "Rw U' Fw2 ...",
  "moves": ["Rw", "U'", "Fw2", "..."],
  "message": "Solved in 42 moves"
}
```

---

## How it works

```
┌─────────────────────────────────────────┐
│  Browser                                │
│  ┌────────────┐   POST /solve           │
│  │ Sticker    │ ─────────────────────►  │
│  │ Editor     │                         │
│  └────────────┘                         │
│        │  solution                      │
│        ▼                                │
│  ┌────────────────────────┐             │
│  │  SolutionViewer        │             │
│  │  <twisty-player>       │             │
│  │  move list + controls  │             │
│  └────────────────────────┘             │
└─────────────────────────────────────────┘
          │ Vite proxy
          ▼
┌─────────────────────────────────────────┐
│  FastAPI (uvicorn, port 8000)           │
│  POST /solve                            │
│   1. validate 96-sticker state          │
│   2. convert color codes → face ids     │
│   3. subprocess: RubiksCube444.solve()  │
│   4. normalize WCA notation             │
│   5. verify: apply moves → solved?      │
│   6. return moves[]                     │
└─────────────────────────────────────────┘
          │ subprocess
          ▼
┌─────────────────────────────────────────┐
│  rubiks-cube-NxNxN-solver               │
│  (dwalton76, CFOP-based 4x4 solver)     │
│  Lookup tables: ~/.rubiks-cube-lookup…  │
└─────────────────────────────────────────┘
```

---

## Notation

The solver and the UI both use **WCA notation**:

| Move | Meaning |
|------|---------|
| `U`, `D`, `F`, `B`, `L`, `R` | Outer face 90° clockwise |
| `X'` | Counter-clockwise |
| `X2` | 180° |
| `Uw`, `Rw`, `Fw` … | Wide (outer 2 layers) |
| `3Rw` | Outer 3 layers |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Backend offline" banner | Start `uvicorn main:app --reload` in `backend/` |
| Solver times out (504) | Lookup tables still downloading – check server logs, wait and retry |
| "Solver returned empty solution" | Verify the cube state is physically valid (correct color counts, valid permutation) |
| `ModuleNotFoundError: rubikscubennnsolver` | Run `pip install git+https://github.com/dwalton76/rubiks-cube-NxNxN-solver.git` inside the venv |
| Sticker net colors look wrong | Ensure you're using the paint tool and clicking the right face |
