# 4×4 Rubik's Cube Solver

A full-stack web application that lets you paint a scrambled 4×4 cube, solve it
with the **rubiks-cube-NxNxN-solver** library, and animate the solution in an
interactive 3D viewer.

```
rubiks-solver/
├── backend/
│   ├── main.py              # FastAPI app (all endpoints)
│   ├── check_solver.py      # smoke-test: scramble → solve → verify
│   ├── Dockerfile           # python:3.11 image with solver pre-installed
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
├── docker-compose.yml  # backend service with persistent table volume
├── run.sh      # Linux / macOS launcher
├── run.bat     # Windows launcher (backend: use WSL2 or Docker)
└── README.md
```

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | **3.11** | The solver pins `setuptools==49.2.0`, which breaks on 3.12+ |
| Node.js | 18 + | |
| npm | 9 + | |
| git | any | Required to clone the solver repo |

> **Platform note:** The solver is **Linux-oriented** — it uses `wget` and
> `gunzip` to fetch lookup tables from S3, and builds C extensions at install
> time. On **Windows**, run the backend in **WSL2** or **Docker**
> (see [`backend/Dockerfile`](backend/Dockerfile) and
> [`docker-compose.yml`](docker-compose.yml)).

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
1. Create a **Python 3.11** virtual environment in `backend/.venv`
2. `git clone` the NxNxN solver then `pip install --no-build-isolation`
3. Install FastAPI + uvicorn from `requirements.txt`
4. Install npm packages in `frontend/`
5. Start the backend on **http://localhost:8000**
6. Start the frontend on **http://localhost:5173**

Open **http://localhost:5173** in your browser.

---

## Manual setup (step by step)

### 1 – Backend

> **Requires Python 3.11.** The solver pins `setuptools==49.2.0`; this breaks
> on Python 3.12+.  Run on Linux/macOS (or WSL2/Docker on Windows).

```bash
cd rubiks-solver/backend

# Create and activate a Python 3.11 venv
python3.11 -m venv .venv
source .venv/bin/activate          # Windows WSL: same; native cmd: .venv\Scripts\activate

# Install FastAPI + uvicorn
pip install -r requirements.txt

# Clone and install the NxNxN cube solver
# (--no-build-isolation is required because the repo pins setuptools==49.2.0)
cd ..
git clone --depth 1 https://github.com/dwalton76/rubiks-cube-NxNxN-solver
cd backend
pip install --no-build-isolation ../rubiks-cube-NxNxN-solver

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

## Running with Docker (recommended on Windows)

The [`backend/Dockerfile`](backend/Dockerfile) builds a `python:3.11-slim`
image with `wget`, `gzip`, `gcc`, and the solver pre-installed.
[`docker-compose.yml`](docker-compose.yml) mounts a host volume so lookup
tables survive container restarts.

```bash
cd rubiks-solver

# Build and start the backend
docker compose up          # add --build after code changes

# Run the frontend separately (native Node is fine on Windows)
cd frontend && npm install && npm run dev
```

The backend is available at **http://localhost:8000**; lookup tables are stored
in `~/.rubiks-cube-lookup-tables` on the host.

---

## First-run solver setup

On the **first `/solve` request** the solver will automatically download its
lookup tables from the internet to:

```
~/.rubiks-cube-lookup-tables/   # Linux / macOS / WSL2
```

Table sizes vary by cube size and algorithm stage; **the first run may download
several hundred MB** in total. This can take several minutes depending on your
connection. The status banner in the UI will say "Solving…". Subsequent solves
run in **under 15 seconds**.

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
│  (dwalton76, reduction method solver)   │
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
| `ModuleNotFoundError: rubikscubennnsolver` | `git clone https://github.com/dwalton76/rubiks-cube-NxNxN-solver` then `pip install --no-build-isolation ./rubiks-cube-NxNxN-solver` inside the venv |
| Sticker net colors look wrong | Ensure you're using the paint tool and clicking the right face |
