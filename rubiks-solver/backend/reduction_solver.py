"""
Lightweight in-memory 4x4 Rubik's Cube Reduction Solver
======================================================
Solves any valid 4x4 Rubik's cube state in pure memory using the reduction method:
  Phase 1: Solve all 6 centers using 3-cycle commutators (A* search).
  Phase 2: Pair all 12 edge pairs using center-preserving edge commutators and L2E BFS.
  Phase 3: Solve the reduced 3x3 state using Kociemba with automatic OLL/PLL parity handling.
  Phase 4: Move cancellation and simplification.

Requires 0 MB of lookup tables on disk (no large downloads, perfect for serverless).
"""

from __future__ import annotations

import heapq
import logging
from collections import deque
from typing import List, Tuple

import kociemba
from rubikscubennnsolver.RubiksCube444 import RubiksCube444, centers_444
from rubikscubennnsolver.swaps import swaps_444

log = logging.getLogger(__name__)


def invert_seq(seq: List[str] | Tuple[str, ...]) -> List[str]:
    """Invert a sequence of Rubik's cube moves."""
    inv: List[str] = []
    for m in reversed(seq):
        if m.endswith("'"):
            inv.append(m[:-1])
        elif m.endswith("2"):
            inv.append(m)
        else:
            inv.append(m + "'")
    return inv


# ── Base Commutators ───────────────────────────────────────────────────────────
# Center 3-cycle commutator: [2R, U 2L' U'] cycles 3 center pieces, touches 0 edges/corners
base_c = ["2R", "U", "2L'", "U'", "2R'", "U", "2L", "U'"]
base_c_inv = invert_seq(base_c)

# Edge pairing commutator: [2U, R U R'] cycles 3 wings, touches 0 centers
base_e1 = ["2U", "R", "U", "R'", "2U'", "R", "U'", "R'"]
base_e1_inv = invert_seq(base_e1)

# Edge flipping algorithm for last two edges (L2E)
flip = ["R", "U", "R'", "F", "R'", "F'", "R"]
l2e_algs = [
    ["2U'"] + flip + ["2U"],
    ["2U"] + flip + ["2U'"],
    flip + ["2U'"] + flip + ["2U"],
    flip + ["2U"] + flip + ["2U'"],
    ["2R2", "B2", "U2", "2L", "U2", "2R'", "U2", "2R", "U2", "F2", "2R", "F2", "2L'", "B2", "2R2"],  # OLL parity
]

oll_parity = ["2R2", "B2", "U2", "2L", "U2", "2R'", "U2", "2R", "U2", "F2", "2R", "F2", "2L'", "B2", "2R2"]
pll_parity = ["2R2", "U2", "2R2", "Uw2", "2R2", "Uw2"]

rotations = [
    [],
    ["x"], ["x'"], ["x2"],
    ["y"], ["y'"], ["y2"],
    ["z"], ["z'"], ["z2"],
    ["x", "y"], ["x", "y'"], ["x", "y2"],
    ["x'", "y"], ["x'", "y'"], ["x'", "y2"],
    ["x2", "y"], ["x2", "y'"],
    ["y", "x"], ["y'", "x"],
    ["z", "x"], ["z'", "x"],
    ["z", "y"], ["z'", "y"],
]

outer_turns = [
    [], ["U"], ["U'"], ["U2"],
    ["D"], ["D'"], ["D2"],
    ["R"], ["R'"], ["R2"],
    ["L"], ["L'"], ["L2"],
    ["F"], ["F'"], ["F2"],
    ["B"], ["B'"], ["B2"],
]

single_outer = ["U", "U'", "U2", "D", "D'", "D2", "R", "R'", "R2", "L", "L'", "L2", "F", "F'", "F2", "B", "B'", "B2"]

edges_info: List[Tuple[str, Tuple[int, int], Tuple[int, int]]] = [
    ("UB", (2, 67), (3, 66)),
    ("UL", (5, 18), (9, 19)),
    ("UR", (8, 51), (12, 50)),
    ("UF", (14, 34), (15, 35)),
    ("BL", (72, 21), (76, 25)),
    ("BR", (69, 56), (73, 60)),
    ("FL", (37, 24), (41, 28)),
    ("FR", (40, 53), (44, 57)),
    ("DF", (82, 46), (83, 47)),
    ("DL", (85, 30), (89, 31)),
    ("DR", (88, 62), (92, 63)),
    ("DB", (94, 79), (95, 78)),
]

edges_dict = {name: (w1, w2) for name, w1, w2 in edges_info}

face_centers = {
    "U": (6, 7, 10, 11),
    "L": (22, 23, 26, 27),
    "F": (38, 39, 42, 43),
    "R": (54, 55, 58, 59),
    "B": (70, 71, 74, 75),
    "D": (86, 87, 90, 91),
}
center_pos_to_target = {}
for face, positions in face_centers.items():
    for p in positions:
        center_pos_to_target[p] = face

target_centers_tuple = tuple(center_pos_to_target[c] for c in centers_444)


def count_correct_centers(c_state: Tuple[str, ...]) -> int:
    return sum(1 for i in range(24) if c_state[i] == target_centers_tuple[i])


def count_unpaired(state: Tuple[str, ...]) -> int:
    cnt = 0
    for name, w1, w2 in edges_info:
        if (state[w1[0]], state[w1[1]]) != (state[w2[0]], state[w2[1]]):
            cnt += 1
    return cnt


def is_edge_unpaired(st: List[str] | Tuple[str, ...], name: str) -> bool:
    w1, w2 = edges_dict[name]
    return (st[w1[0]], st[w1[1]]) != (st[w2[0]], st[w2[1]])


# ── Precompute Center Moves ───────────────────────────────────────────────────
_all_c_dict: dict[Tuple[int, ...], Tuple[str, ...]] = {}
for _rot in rotations:
    _rot_inv = invert_seq(_rot)
    for _u in [[], ["U"], ["U'"], ["U2"]]:
        _u_inv = invert_seq(_u)
        for _f in [[], ["F"], ["F'"], ["F2"]]:
            _f_inv = invert_seq(_f)
            _setup = _rot + _u + _f
            _setup_inv = _f_inv + _u_inv + _rot_inv
            for _base in [base_c, base_c_inv]:
                _full = tuple(_setup + _base + _setup_inv)
                _st = list(range(97))
                for _m in _full:
                    _st = [_st[_x] for _x in swaps_444[_m]]
                _perm = tuple(_st[_c] for _c in centers_444)
                if _perm not in _all_c_dict:
                    _all_c_dict[_perm] = _full

_c_idx = {c: i for i, c in enumerate(centers_444)}
c_perm_indices: List[Tuple[Tuple[int, ...], Tuple[str, ...]]] = []
for _perm, _seq in _all_c_dict.items():
    _idx_map = tuple(_c_idx[_perm[i]] for i in range(24))
    c_perm_indices.append((_idx_map, _seq))


# ── Precompute Edge Moves ─────────────────────────────────────────────────────
_edge_moves_dict: dict[Tuple[int, ...], Tuple[str, ...]] = {}
for _rot in rotations:
    _rot_inv = invert_seq(_rot)
    for _out in outer_turns:
        _out_inv = invert_seq(_out)
        _setup = _rot + _out
        _setup_inv = _out_inv + _rot_inv
        for _base in [base_e1, base_e1_inv]:
            _full = tuple(_setup + _base + _setup_inv)
            _st = list(range(97))
            for _m in _full:
                _st = [_st[_x] for _x in swaps_444[_m]]
            if all(_st[_c] == _c for _c in centers_444):
                _perm = tuple(_st)
                if _perm not in _edge_moves_dict:
                    _edge_moves_dict[_perm] = _full

edge_moves: List[Tuple[Tuple[int, ...], Tuple[str, ...]]] = list(_edge_moves_dict.items())


# ── Solvers ───────────────────────────────────────────────────────────────────
def solve_centers(initial_state: Tuple[str, ...]) -> List[str]:
    """A* search to group all 24 center pieces to matching faces."""
    frontier = []
    initial_score = 24 - count_correct_centers(initial_state)
    heapq.heappush(frontier, (initial_score, 0, initial_state, []))
    visited = {initial_state: 0}

    while frontier:
        score, depth, state, path = heapq.heappop(frontier)
        if score == 0:
            return path
        for idx_map, seq in c_perm_indices:
            new_state = tuple(state[idx_map[i]] for i in range(24))
            new_score = 24 - count_correct_centers(new_state)
            if new_score <= score + 1:
                if new_state not in visited or visited[new_state] > depth + 1:
                    visited[new_state] = depth + 1
                    heapq.heappush(frontier, (new_score, depth + 1, new_state, path + list(seq)))
    raise ValueError("Could not solve centers")


def find_l2e_solution(state: List[str] | Tuple[str, ...]) -> List[str]:
    """BFS to position the last 2 unpaired edges at FL & FR and apply L2E algorithms."""
    if count_unpaired(tuple(state)) == 0:
        return []

    queue = deque([([], list(state))])
    visited = set()

    while queue:
        path, cur_st = queue.popleft()
        if is_edge_unpaired(cur_st, "FL") and is_edge_unpaired(cur_st, "FR"):
            inv_path = invert_seq(path)
            for alg in l2e_algs:
                test_st = list(cur_st)
                for m in alg:
                    test_st = [test_st[x] for x in swaps_444[m]]
                for m in inv_path:
                    test_st = [test_st[x] for x in swaps_444[m]]
                if count_unpaired(tuple(test_st)) == 0:
                    return path + alg + inv_path

        if len(path) < 3:
            for m in single_outer:
                nxt = [cur_st[x] for x in swaps_444[m]]
                key = tuple(nxt[w1[0]] for name, w1, w2 in edges_info)
                if key not in visited:
                    visited.add(key)
                    queue.append((path + [m], nxt))

    # Whole-cube rotation fallback
    for rot in rotations:
        rot_inv = invert_seq(rot)
        for alg in l2e_algs:
            full = rot + alg + rot_inv
            test_st = list(state)
            for m in full:
                test_st = [test_st[x] for x in swaps_444[m]]
            if count_unpaired(tuple(test_st)) == 0:
                return full
    raise ValueError("Failed to solve last 2 edges")


def solve_edges(cube_state: Tuple[str, ...]) -> List[str]:
    """Beam search using 3-cycle edge commutators down to L2E, then solves L2E."""
    beam_width = 30
    curr_beam = [(count_unpaired(cube_state), cube_state, [])]
    visited = {cube_state: 0}
    state_with_2 = None
    path_to_2 = None

    for step in range(15):
        best_score = min(b[0] for b in curr_beam)
        if best_score <= 2:
            for b in curr_beam:
                if b[0] == best_score:
                    state_with_2 = b[1]
                    path_to_2 = b[2]
                    break
            if best_score == 0:
                return path_to_2
            break

        next_candidates = []
        for score, st, path in curr_beam:
            for perm, seq in edge_moves:
                new_st = tuple(st[perm[i]] for i in range(97))
                new_score = count_unpaired(new_st)
                if new_score <= score:
                    if new_st not in visited:
                        visited[new_st] = step + 1
                        next_candidates.append((new_score, new_st, path + list(seq)))
        next_candidates.sort(key=lambda x: x[0])
        seen_in_beam = set()
        new_beam = []
        for cand in next_candidates:
            if cand[1] not in seen_in_beam:
                seen_in_beam.add(cand[1])
                new_beam.append(cand)
                if len(new_beam) >= beam_width:
                    break
        curr_beam = new_beam

    if state_with_2 is not None and count_unpaired(state_with_2) > 0:
        l2e_seq = find_l2e_solution(state_with_2)
        return path_to_2 + l2e_seq

    return path_to_2 or []


def solve_333_stage(cube: RubiksCube444) -> None:
    """Solve the reduced 3x3 cube with Kociemba, fixing OLL/PLL parity if encountered."""
    if cube.solved():
        return

    for attempt in range(6):
        if cube.solved():
            return
        k_str = cube.get_kociemba_string(False)
        if k_str == "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB":
            if cube.solved():
                return
        try:
            solution_str = kociemba.solve(k_str).strip()
            if solution_str:
                for step in solution_str.split():
                    cube.rotate(step)
            if cube.solved():
                return
        except Exception as e:
            err = str(e)
            if "Flip error" in err or "Error 3" in err:
                for m in oll_parity:
                    cube.rotate(m)
            elif "Parity error" in err or "Error 6" in err:
                for m in pll_parity:
                    cube.rotate(m)
            else:
                for m in oll_parity:
                    cube.rotate(m)

    if not cube.solved():
        raise ValueError("Could not solve 3x3 stage after parity fixes")


def simplify_moves(moves: List[str]) -> List[str]:
    """Combine consecutive moves on the same face and cancel redundant turns."""
    res: List[str] = []

    def parse(m: str) -> Tuple[str, int]:
        if m.endswith("'"):
            return m[:-1], 3
        elif m.endswith("2"):
            return m[:-1], 2
        else:
            return m, 1

    def format_move(base: str, amount: int) -> str | None:
        amount = amount % 4
        if amount == 0:
            return None
        elif amount == 1:
            return base
        elif amount == 2:
            return base + "2"
        elif amount == 3:
            return base + "'"
        return None

    for m in moves:
        if not m:
            continue
        base, amt = parse(m)
        if res and parse(res[-1])[0] == base:
            prev_base, prev_amt = parse(res.pop())
            combined = (prev_amt + amt) % 4
            new_m = format_move(base, combined)
            if new_m:
                res.append(new_m)
        else:
            res.append(m)
    return res


def solve_444(cube_state_str: str) -> List[str]:
    """
    Main entry point: reduce and solve a 4x4 Rubik's Cube state string.
    Returns a clean list of WCA move strings.
    """
    cube = RubiksCube444(cube_state_str, "ULFRBD")
    if cube.solved():
        return []

    init_solution_len = len(cube.solution)

    # 1. Centers
    c_path = solve_centers(tuple(cube.state[c] for c in centers_444))
    for m in c_path:
        cube.rotate(m)

    # 2. Edges
    e_path = solve_edges(tuple(cube.state))
    for m in e_path:
        cube.rotate(m)

    # 3. 3x3 stage & Parity
    solve_333_stage(cube)

    # Extract all moves applied during this solve session
    raw_moves = [m for m in cube.solution[init_solution_len:] if not m.startswith("COMMENT")]

    # Simplify consecutive moves iteratively
    cur = raw_moves
    while True:
        nxt = simplify_moves(cur)
        if len(nxt) == len(cur):
            break
        cur = nxt

    return cur
