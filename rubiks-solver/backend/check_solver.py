#!/usr/bin/env python3
"""
check_solver.py – Smoke-test for the rubiks-cube-NxNxN-solver integration.

What it does:
  1. Builds a RubiksCube444 in the solved state.
  2. Applies a fixed 20-move scramble via cube.rotate().
  3. Calls cube.solve().
  4. Applies every move in cube.solution (skipping COMMENT entries).
  5. Asserts the cube is back to solved.

Run from rubiks-solver/backend/:
  python check_solver.py

Exit code 0 = PASS, 1 = FAIL.
"""

import sys
import traceback

# ── Fixed 20-move scramble ─────────────────────────────────────────────────────
# Chosen to exercise wide moves and double-layer turns on a 4x4.
SCRAMBLE = [
    "Rw", "U", "Fw2", "Rw'", "U2",
    "Fw", "U'", "Rw", "U2", "Fw'",
    "Rw2", "U", "Fw'", "Rw", "U'",
    "Fw2", "Rw", "U'", "Fw'", "Rw'",
]

# Solved-state string in ULFRBD order (16 of each face letter)
SOLVED_STRING = (
    "U" * 16 + "L" * 16 + "F" * 16 +
    "R" * 16 + "B" * 16 + "D" * 16
)


def is_solved(cube) -> bool:
    """Return True if every face of the cube is a single uniform colour.

    cube.state has a dummy 'x' at index 0 (97 entries total).
    Real stickers are state[1:97], i.e. face i occupies state[1+i*16 : 1+(i+1)*16].
    """
    state = cube.state
    for i in range(6):
        face = state[1 + i * 16 : 1 + (i + 1) * 16]
        if len(set(face)) != 1:
            return False
    return True


def main() -> int:
    print("=" * 60)
    print("check_solver.py – rubiks-cube-NxNxN-solver smoke test")
    print("=" * 60)

    # ── Step 1: import solver ──────────────────────────────────────────────────
    print("\n[1/5] Importing RubiksCube444 …", end=" ", flush=True)
    try:
        from rubikscubennnsolver.RubiksCube444 import RubiksCube444
    except ImportError as exc:
        print("FAIL")
        print(f"\nERROR: Could not import solver: {exc}")
        print(
            "\nInstall the solver first:\n"
            "  git clone https://github.com/dwalton76/rubiks-cube-NxNxN-solver\n"
            "  pip install --no-build-isolation ./rubiks-cube-NxNxN-solver\n"
        )
        return 1
    print("OK")

    # ── Step 2: build a solved cube ────────────────────────────────────────────
    print("[2/5] Building solved cube …", end=" ", flush=True)
    try:
        cube = RubiksCube444(SOLVED_STRING, "ULFRBD")
        assert is_solved(cube), "Cube is not solved after construction"
    except Exception as exc:
        print("FAIL")
        print(f"\nERROR: {exc}")
        traceback.print_exc()
        return 1
    print("OK")

    # ── Step 3: apply scramble ────────────────────────────────────────────────
    print(f"[3/5] Applying {len(SCRAMBLE)}-move scramble …", end=" ", flush=True)
    scramble_str = " ".join(SCRAMBLE)
    print(f"({scramble_str})", end=" ", flush=True)
    try:
        for move in SCRAMBLE:
            cube.rotate(move)
        assert not is_solved(cube), "Cube appears solved immediately after scramble – something is wrong"
        scrambled_state_str = "".join(cube.state[1:])
    except Exception as exc:
        print("FAIL")
        print(f"\nERROR: {exc}")
        traceback.print_exc()
        return 1
    print("OK")

    # ── Step 4: solve ─────────────────────────────────────────────────────────
    print("[4/5] Solving (may take a while on first run) …", flush=True)
    try:
        solve_cube = RubiksCube444(scrambled_state_str, "ULFRBD")
        solve_cube.solve()
        solution_moves = [
            m for m in solve_cube.solution
            if not m.startswith("COMMENT")
        ]
        print(f"      Solution: {len(solution_moves)} moves")
        if solution_moves:
            preview = " ".join(solution_moves[:15])
            suffix = " …" if len(solution_moves) > 15 else ""
            print(f"      First 15: {preview}{suffix}")
    except Exception as exc:
        print("FAIL")
        print(f"\nERROR during solve: {exc}")
        traceback.print_exc()
        return 1

    # ── Step 5: apply solution and verify ─────────────────────────────────────
    print("[5/5] Applying solution and verifying …", end=" ", flush=True)
    try:
        for move in solution_moves:
            cube.rotate(move)
        solved = is_solved(cube)
    except Exception as exc:
        print("FAIL")
        print(f"\nERROR while applying solution: {exc}")
        traceback.print_exc()
        return 1

    if not solved:
        print("FAIL")
        face_labels = ["U", "L", "F", "R", "B", "D"]
        state = cube.state
        print("\nFinal cube state is NOT solved. Face dump:")
        for i, label in enumerate(face_labels):
            # state[0] is the dummy 'x'; real stickers start at index 1
            face = state[1 + i * 16 : 1 + (i + 1) * 16]
            print(f"  {label}: {''.join(face)}")
        return 1

    print("OK")
    print("\n" + "=" * 60)
    print("PASS - scramble -> solve -> verify completed successfully.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
