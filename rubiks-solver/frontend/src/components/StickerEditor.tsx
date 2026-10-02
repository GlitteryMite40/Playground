import { useState } from "react";
import type { CubeColor, CubeState, FaceName } from "../types/cube";
import {
  COLOR_CSS,
  COLOR_LABEL,
  COLOR_ORDER,
  countColors,
  isStateValid,
  makeSolvedState,
} from "../utils/cubeUtils";

interface Props {
  state: CubeState;
  onChange: (state: CubeState) => void;
  onSolve: () => void;
  onDemo: () => void;
  solving: boolean;
  demoLoading: boolean;
}

// The 4x4 cube net is laid out as a cross:
//
//         [ U ]
// [ L ]   [ F ]   [ R ]   [ B ]
//         [ D ]
//
// Each cell in the layout grid is either a face name or null (empty space).
const NET_LAYOUT: (FaceName | null)[][] = [
  [null, "U", null, null],
  ["L", "F", "R", "B"],
  [null, "D", null, null],
];

export default function StickerEditor({
  state,
  onChange,
  onSolve,
  onDemo,
  solving,
  demoLoading,
}: Props) {
  const [paintColor, setPaintColor] = useState<CubeColor>("W");

  const counts = countColors(state);
  const valid = isStateValid(state);

  function handleStickerClick(face: FaceName, idx: number) {
    const newFace = [...state[face]] as CubeColor[];
    newFace[idx] = paintColor;
    onChange({ ...state, [face]: newFace });
  }

  function handleReset() {
    onChange(makeSolvedState());
  }

  return (
    <div className="card">
      <div className="card-title">Cube State Editor</div>

      {/* Paint color selector */}
      <div className="color-picker-row">
        <label>Paint color:</label>
        {COLOR_ORDER.map((c) => (
          <button
            key={c}
            className={`color-swatch${paintColor === c ? " selected" : ""}`}
            style={{ background: COLOR_CSS[c] }}
            title={COLOR_LABEL[c]}
            onClick={() => setPaintColor(c)}
            aria-label={`Select ${COLOR_LABEL[c]}`}
          />
        ))}
      </div>

      {/* Color counters */}
      <div className="color-counters">
        {COLOR_ORDER.map((c) => (
          <div key={c} className={`color-badge ${counts[c] === 16 ? "ok" : "bad"}`}>
            <span
              className="color-badge-dot"
              style={{ background: COLOR_CSS[c] }}
            />
            <span>{COLOR_LABEL[c]}</span>
            <span className="badge-count" style={{ marginLeft: 4 }}>
              {counts[c]}/16
            </span>
          </div>
        ))}
      </div>

      {/* Cube net */}
      <div className="net-wrapper">
        {NET_LAYOUT.map((row, rowIdx) => (
          <div key={rowIdx} className="net-row">
            {row.map((cell, colIdx) =>
              cell === null ? (
                <div key={colIdx} className="face-spacer" />
              ) : (
                <FaceGrid
                  key={colIdx}
                  face={cell}
                  stickers={state[cell]}
                  onClick={(idx) => handleStickerClick(cell, idx)}
                />
              )
            )}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="action-row">
        <button
          className="btn-primary"
          disabled={!valid || solving}
          onClick={onSolve}
          title={valid ? "Solve the cube" : "Each color must have exactly 16 stickers"}
        >
          {solving ? (
            <>
              <span className="spinner" />
              Solving…
            </>
          ) : (
            "Solve"
          )}
        </button>

        <button
          className="btn-secondary"
          onClick={onDemo}
          disabled={demoLoading || solving}
        >
          {demoLoading ? (
            <>
              <span className="spinner" />
              Loading…
            </>
          ) : (
            "Load demo scramble"
          )}
        </button>

        <button className="btn-secondary" onClick={handleReset} disabled={solving}>
          Reset to solved
        </button>
      </div>
    </div>
  );
}

// ── Face grid sub-component ───────────────────────────────────────────────────
interface FaceGridProps {
  face: FaceName;
  stickers: CubeColor[];
  onClick: (idx: number) => void;
}

function FaceGrid({ face, stickers, onClick }: FaceGridProps) {
  return (
    <div>
      <div
        style={{
          textAlign: "center",
          fontSize: 11,
          color: "#8892a4",
          marginBottom: 3,
          fontWeight: 600,
          letterSpacing: 1,
        }}
      >
        {face}
      </div>
      <div className="face-block">
        {stickers.map((color, idx) => (
          <button
            key={idx}
            className="sticker"
            style={{ background: COLOR_CSS[color] }}
            onClick={() => onClick(idx)}
            title={`${face}[${Math.floor(idx / 4)},${idx % 4}] = ${COLOR_LABEL[color]}`}
            aria-label={`Face ${face} sticker ${idx}: ${COLOR_LABEL[color]}`}
          />
        ))}
      </div>
    </div>
  );
}
