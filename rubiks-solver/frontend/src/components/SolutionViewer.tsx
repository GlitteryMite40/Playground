import {
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
// cubing exports TwistyPlayer as a custom element; we import it for side effects
import "cubing/twisty";

interface Props {
  moves: string[];
  setupAlg: string; // inverse of solution — sets the scrambled state
  onBack: () => void;
}

// Speed label <-> ms per move
const SPEEDS = [
  { label: "0.25×", ms: 2000 },
  { label: "0.5×", ms: 1000 },
  { label: "1×", ms: 500 },
  { label: "1.5×", ms: 333 },
  { label: "2×", ms: 250 },
  { label: "3×", ms: 167 },
];

export default function SolutionViewer({ moves, setupAlg, onBack }: Props) {
  const [currentMove, setCurrentMove] = useState(0); // 0 = before any move
  const [playing, setPlaying] = useState(false);
  const [speedIdx, setSpeedIdx] = useState(2); // default 1×
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const twistyRef = useRef<HTMLElement | null>(null);

  const total = moves.length;

  // ── Build the alg up to currentMove for twisty-player ──────────────────────
  const algUpToCurrent = moves.slice(0, currentMove).join(" ");

  // ── Auto-play logic ─────────────────────────────────────────────────────────
  const stopPlay = useCallback(() => {
    setPlaying(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!playing) return;
    if (currentMove >= total) {
      stopPlay();
      return;
    }
    const ms = SPEEDS[speedIdx].ms;
    intervalRef.current = setInterval(() => {
      setCurrentMove((prev) => {
        if (prev >= total) {
          stopPlay();
          return prev;
        }
        return prev + 1;
      });
    }, ms);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, speedIdx, total, stopPlay]); // re-run when speed changes

  // stop if we reach the end
  useEffect(() => {
    if (currentMove >= total && playing) stopPlay();
  }, [currentMove, total, playing, stopPlay]);

  function togglePlay() {
    if (playing) {
      stopPlay();
    } else {
      if (currentMove >= total) setCurrentMove(0);
      setPlaying(true);
    }
  }

  function stepBack() {
    stopPlay();
    setCurrentMove((p) => Math.max(0, p - 1));
  }
  function stepForward() {
    stopPlay();
    setCurrentMove((p) => Math.min(total, p + 1));
  }
  function jumpTo(idx: number) {
    stopPlay();
    setCurrentMove(idx + 1); // clicking move N shows state after move N
  }

  // ── Scroll current chip into view ───────────────────────────────────────────
  const chipRef = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    chipRef.current?.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
  }, [currentMove]);

  // ── Update twisty-player attributes imperatively ────────────────────────────
  // twisty-player is a custom element; setting attributes triggers its internal re-render
  useEffect(() => {
    const el = twistyRef.current as HTMLElement & Record<string, unknown> | null;
    if (!el) return;
    el.setAttribute("experimental-setup-alg", setupAlg);
    el.setAttribute("alg", algUpToCurrent || "");
    el.setAttribute("puzzle", "4x4x4");
    el.setAttribute("visualization", "3D");
    el.setAttribute("camera-latitude", "30");
    el.setAttribute("camera-longitude", "25");
    el.setAttribute("back-view", "none");
    el.setAttribute("control-panel", "none");
    el.setAttribute("tempo-scale", "2");
  }, [setupAlg, algUpToCurrent]);

  return (
    <div className="card">
      <div className="solution-header">
        <h2>Solution</h2>
        <span className="move-count">{total} moves</span>
        <button className="btn-secondary" style={{ marginLeft: "auto" }} onClick={onBack}>
          ← Edit cube
        </button>
      </div>

      {/* 3D Viewer */}
      <div className="twisty-container">
        <twisty-player
          ref={twistyRef}
          puzzle="4x4x4"
          visualization="3D"
          experimental-setup-alg={setupAlg}
          alg={algUpToCurrent || ""}
          control-panel="none"
          back-view="none"
          tempo-scale="2"
          camera-latitude="30"
          camera-longitude="25"
        />
      </div>

      {/* Move list */}
      <div className="move-list-wrapper">
        <div className="move-list">
          {moves.map((move, idx) => (
            <button
              key={idx}
              ref={idx + 1 === currentMove ? chipRef : null}
              className={`move-chip${
                idx + 1 === currentMove
                  ? " current"
                  : idx < currentMove
                  ? " done"
                  : ""
              }`}
              onClick={() => jumpTo(idx)}
              title={`Jump to after move ${idx + 1}: ${move}`}
            >
              {move}
            </button>
          ))}
        </div>
      </div>

      {/* Playback controls */}
      <div className="playback-controls">
        <button
          className="btn-icon"
          onClick={() => { stopPlay(); setCurrentMove(0); }}
          disabled={currentMove === 0}
          title="Jump to start"
        >
          ⏮
        </button>
        <button
          className="btn-icon"
          onClick={stepBack}
          disabled={currentMove === 0}
          title="Step back"
        >
          ◀
        </button>
        <button
          className="btn-icon"
          onClick={togglePlay}
          title={playing ? "Pause" : "Play"}
          style={{ minWidth: 44 }}
        >
          {playing ? "⏸" : "▶"}
        </button>
        <button
          className="btn-icon"
          onClick={stepForward}
          disabled={currentMove >= total}
          title="Step forward"
        >
          ▶
        </button>
        <button
          className="btn-icon"
          onClick={() => { stopPlay(); setCurrentMove(total); }}
          disabled={currentMove === total}
          title="Jump to end"
        >
          ⏭
        </button>

        <span className="step-indicator">
          {currentMove} / {total}
        </span>

        <div className="speed-control">
          <span>Speed:</span>
          <input
            type="range"
            min={0}
            max={SPEEDS.length - 1}
            value={speedIdx}
            onChange={(e) => {
              const v = Number(e.target.value);
              setSpeedIdx(v);
              // restart interval at new speed if currently playing
              if (playing) {
                stopPlay();
                setTimeout(() => setPlaying(true), 10);
              }
            }}
          />
          <span>{SPEEDS[speedIdx].label}</span>
        </div>
      </div>
    </div>
  );
}
