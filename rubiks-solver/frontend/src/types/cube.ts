// Color identifiers
export type CubeColor = "W" | "Y" | "G" | "B" | "R" | "O";

// A face is 16 stickers (4x4), index 0..15 in reading order
export type Face = CubeColor[];

// The full cube state: 6 faces × 16 stickers = 96 stickers
// Face order: U, L, F, R, B, D  (matches rubikscubennnsolver kociemba ordering)
export interface CubeState {
  U: Face; // White
  L: Face; // Orange
  F: Face; // Green
  R: Face; // Red
  B: Face; // Blue
  D: Face; // Yellow
}

export type FaceName = keyof CubeState;

export interface SolveRequest {
  state: string[]; // 96 chars, ULFRBD order
}

export interface SolveResponse {
  solution: string;   // space-separated WCA moves
  moves: string[];    // parsed array
  message?: string;
}

export interface DemoResponse {
  state: string[];    // 96 color codes
  scramble: string;   // the scramble that was applied
}
