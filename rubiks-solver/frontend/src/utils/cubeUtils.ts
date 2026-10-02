import type { CubeColor, CubeState, FaceName } from "../types/cube";

// ── Canonical color cycle order ───────────────────────────────────────────────
export const COLOR_ORDER: CubeColor[] = ["W", "Y", "G", "B", "R", "O"];

// CSS colors for each cube color
export const COLOR_CSS: Record<CubeColor, string> = {
  W: "#ffffff",
  Y: "#ffd500",
  G: "#009b48",
  B: "#0046ad",
  R: "#b71234",
  O: "#ff5800",
};

export const COLOR_LABEL: Record<CubeColor, string> = {
  W: "White",
  Y: "Yellow",
  G: "Green",
  B: "Blue",
  R: "Red",
  O: "Orange",
};

// Default face color (center color) per face
export const FACE_DEFAULT_COLOR: Record<FaceName, CubeColor> = {
  U: "W",
  D: "Y",
  F: "G",
  B: "B",
  R: "R",
  L: "O",
};

// Face display labels
export const FACE_LABELS: Record<FaceName, string> = {
  U: "U (Top/White)",
  D: "D (Bottom/Yellow)",
  F: "F (Front/Green)",
  B: "B (Back/Blue)",
  R: "R (Right/Red)",
  L: "L (Left/Orange)",
};

// Face order for the solver (must match rubikscubennnsolver expectation)
export const FACE_ORDER: FaceName[] = ["U", "L", "F", "R", "B", "D"];

// ── Solved state ──────────────────────────────────────────────────────────────
export function makeSolvedState(): CubeState {
  return {
    U: Array(16).fill("W") as CubeColor[],
    L: Array(16).fill("O") as CubeColor[],
    F: Array(16).fill("G") as CubeColor[],
    R: Array(16).fill("R") as CubeColor[],
    B: Array(16).fill("B") as CubeColor[],
    D: Array(16).fill("Y") as CubeColor[],
  };
}

// ── Color counting ────────────────────────────────────────────────────────────
export function countColors(state: CubeState): Record<CubeColor, number> {
  const counts: Record<CubeColor, number> = { W: 0, Y: 0, G: 0, B: 0, R: 0, O: 0 };
  for (const face of FACE_ORDER) {
    for (const c of state[face]) {
      counts[c]++;
    }
  }
  return counts;
}

export function isStateValid(state: CubeState): boolean {
  const counts = countColors(state);
  return (Object.values(counts) as number[]).every((n) => n === 16);
}

// ── Cycle a sticker's color ───────────────────────────────────────────────────
export function cycleColor(color: CubeColor): CubeColor {
  const idx = COLOR_ORDER.indexOf(color);
  return COLOR_ORDER[(idx + 1) % COLOR_ORDER.length];
}

// ── State serialisation ───────────────────────────────────────────────────────
// Returns 96-element array of color codes in ULFRBD face order
export function stateToArray(state: CubeState): string[] {
  const result: string[] = [];
  for (const face of FACE_ORDER) {
    result.push(...state[face]);
  }
  return result;
}

export function arrayToState(arr: string[]): CubeState {
  const state = makeSolvedState();
  let i = 0;
  for (const face of FACE_ORDER) {
    state[face] = arr.slice(i, i + 16) as CubeColor[];
    i += 16;
  }
  return state;
}
