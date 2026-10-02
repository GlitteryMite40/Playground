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
  setupAlg?: string;
  onBack: () => void;
}

// Speed labels and playback tempo multiplier for twisty-player
const SPEEDS = [
  { label: "0.5×", scale: 0.5 },
  { label: "1×", scale: 1 },
  { label: "1.5×", scale: 1.5 },
  { label: "2×", scale: 2 },
  { label: "3×", scale: 3 },
  { label: "5×", scale: 5 },
];

export default function SolutionViewer({ moves, onBack }: Props) {
  const [currentMove, setCurrentMove] = useState(0); // 0 = start (scrambled)
  const [playing, setPlaying] = useState(false);
  const [speedIdx, setSpeedIdx] = useState(2); // default 1.5×
  const twistyRef = useRef<HTMLElement | null>(null);
  const chipRef = useRef<HTMLButtonElement | null>(null);

  const total = moves.length;
  const fullAlg = moves.join(" ");

  // ── Helper to access the underlying TwistyPlayer ──────────────────────────
  const getPlayer = useCallback(() => {
    return twistyRef.current as (HTMLElement & {
      timeline?: {
        timestamp: number;
        animating: boolean;
        tempoScale: number;
        play(): void;
        pause(): void;
        setTimestamp(ts: number): void;
        jumpToEnd(): void;
        maxTimestamp(): number;
        experimentalPlay(dir: number, boundary: number): void;
        addTimestampListener(l: unknown): void;
        removeTimestampListener(l: unknown): void;
        addActionListener(l: unknown): void;
        removeActionListener(l: unknown): void;
      };
      cursor?: {
        indexer: {
          timestampToIndex(ts: number): number;
          indexToMoveStartTimestamp(idx: number): number;
          moveDuration(idx: number): number;
          numAnimatedLeaves(): number;
        };
      };
    }) | null;
  }, []);

  // ── Sync timeline events with React state ──────────────────────────────────
  useEffect(() => {
    const player = getPlayer();
    if (!player) return;

    if (player.timeline) {
      player.timeline.tempoScale = SPEEDS[speedIdx].scale;
    }

    const timestampListener = {
      onTimelineTimestampChange: (timestamp: number) => {
        const p = getPlayer();
        if (!p?.timeline) return;

        if (timestamp <= 0) {
          setCurrentMove(0);
          return;
        }

        const maxTs = p.timeline.maxTimestamp();
        if (maxTs > 0 && timestamp >= maxTs - 10) {
          setCurrentMove(total);
          return;
        }

        const idxer = p.cursor?.indexer;
        if (idxer) {
          const idx = idxer.timestampToIndex(timestamp);
          setCurrentMove(idx + 1);
        }
      },
      onTimeRangeChange: () => {},
    };

    const actionListener = {
      onTimelineAction: (event: { action: string }) => {
        if (event.action === "StartingToPlay") {
          setPlaying(true);
        } else if (event.action === "Pausing") {
          setPlaying(false);
        }
      },
    };

    if (player.timeline) {
      player.timeline.addTimestampListener(timestampListener);
      player.timeline.addActionListener(actionListener);
    }

    const onInitialized = () => {
      if (player.timeline) {
        player.timeline.tempoScale = SPEEDS[speedIdx].scale;
      }
    };
    player.addEventListener("initialized", onInitialized);

    return () => {
      if (player.timeline) {
        player.timeline.removeTimestampListener(timestampListener);
        player.timeline.removeActionListener(actionListener);
      }
      player.removeEventListener("initialized", onInitialized);
    };
  }, [getPlayer, total, speedIdx]);

  // ── Controls ───────────────────────────────────────────────────────────────
  function togglePlay() {
    const player = getPlayer();
    if (!player?.timeline) return;

    if (playing) {
      player.timeline.pause();
    } else {
      if (player.timeline.timestamp >= player.timeline.maxTimestamp()) {
        player.timeline.setTimestamp(0);
      }
      player.timeline.play();
    }
  }

  function stepBack() {
    const player = getPlayer();
    if (!player?.timeline) return;
    player.timeline.pause();
    // Direction.Backwards = -1, BoundaryType.Move = 0
    player.timeline.experimentalPlay(-1, 0);
  }

  function stepForward() {
    const player = getPlayer();
    if (!player?.timeline) return;
    player.timeline.pause();
    // Direction.Forwards = 1, BoundaryType.Move = 0
    player.timeline.experimentalPlay(1, 0);
  }

  function jumpToStart() {
    const player = getPlayer();
    if (!player?.timeline) return;
    player.timeline.pause();
    player.timeline.setTimestamp(0);
    setCurrentMove(0);
  }

  function jumpToEnd() {
    const player = getPlayer();
    if (!player?.timeline) return;
    player.timeline.pause();
    player.timeline.jumpToEnd();
    setCurrentMove(total);
  }

  function jumpToMove(idx: number) {
    const player = getPlayer();
    if (!player?.timeline) return;
    player.timeline.pause();
    const idxer = player.cursor?.indexer;
    if (idxer) {
      const endTs = idxer.indexToMoveStartTimestamp(idx) + idxer.moveDuration(idx);
      player.timeline.setTimestamp(endTs);
    }
    setCurrentMove(idx + 1);
  }

  function handleSpeedChange(newIdx: number) {
    setSpeedIdx(newIdx);
    const player = getPlayer();
    if (player?.timeline) {
      player.timeline.tempoScale = SPEEDS[newIdx].scale;
    }
  }

  // ── Scroll current chip into view ───────────────────────────────────────────
  useEffect(() => {
    chipRef.current?.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
  }, [currentMove]);

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
          alg={fullAlg}
          experimental-setup-anchor="end"
          camera-latitude="30"
          camera-longitude="25"
          back-view="none"
          control-panel="none"
          background="none"
        />
      </div>

      {/* Scrubber slider */}
      <div className="scrubber-wrapper">
        <input
          type="range"
          min={0}
          max={total}
          value={currentMove}
          onChange={(e) => {
            const val = Number(e.target.value);
            if (val === 0) {
              jumpToStart();
            } else if (val >= total) {
              jumpToEnd();
            } else {
              jumpToMove(val - 1);
            }
          }}
          className="timeline-slider"
          title={`Move ${currentMove} of ${total}`}
          aria-label="Solution progress slider"
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
              onClick={() => jumpToMove(idx)}
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
          onClick={jumpToStart}
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
          onClick={jumpToEnd}
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
            onChange={(e) => handleSpeedChange(Number(e.target.value))}
          />
          <span>{SPEEDS[speedIdx].label}</span>
        </div>
      </div>
    </div>
  );
}
