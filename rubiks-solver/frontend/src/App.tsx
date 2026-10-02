import { useEffect, useState } from "react";
import StickerEditor from "./components/StickerEditor";
import SolutionViewer from "./components/SolutionViewer";
import type { CubeState } from "./types/cube";
import { makeSolvedState, stateToArray, arrayToState } from "./utils/cubeUtils";
import { solveCube, fetchDemo, checkHealth } from "./utils/api";

// Compute inverse of a WCA move sequence (for twisty-player setup-alg)
function invertMoves(moves: string[]): string {
  return [...moves]
    .reverse()
    .map((m) => {
      if (m.endsWith("'")) return m.slice(0, -1);
      if (m.endsWith("2")) return m; // 180° is its own inverse
      return m + "'";
    })
    .join(" ");
}

type AppView = "editor" | "solution";

interface SolutionData {
  moves: string[];
  setupAlg: string;
}

export default function App() {
  const [cubeState, setCubeState] = useState<CubeState>(makeSolvedState);
  const [view, setView] = useState<AppView>("editor");
  const [solution, setSolution] = useState<SolutionData | null>(null);

  const [solving, setSolving] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [status, setStatus] = useState<{ type: "info" | "error" | "success"; msg: string } | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  // Check backend health on mount
  useEffect(() => {
    checkHealth().then((ok) => {
      setBackendOnline(ok);
      if (!ok) {
        setStatus({
          type: "error",
          msg: "Backend is offline. Start the FastAPI server: cd backend && uvicorn main:app --reload",
        });
      }
    });
  }, []);

  async function handleSolve() {
    setSolving(true);
    setStatus({ type: "info", msg: "Sending to solver… This may take 1–3 minutes on first run while lookup tables download." });
    try {
      const arr = stateToArray(cubeState);
      const resp = await solveCube(arr);
      const setupAlg = invertMoves(resp.moves);
      setSolution({ moves: resp.moves, setupAlg });
      setStatus({ type: "success", msg: `Solved in ${resp.moves.length} moves!` });
      setView("solution");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatus({ type: "error", msg: `Solver error: ${msg}` });
    } finally {
      setSolving(false);
    }
  }

  async function handleDemo() {
    setDemoLoading(true);
    setStatus(null);
    try {
      const resp = await fetchDemo();
      setCubeState(arrayToState(resp.state));
      setStatus({ type: "info", msg: `Demo scramble loaded: ${resp.scramble}` });
      setView("editor");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatus({ type: "error", msg: `Demo error: ${msg}` });
    } finally {
      setDemoLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>4×4 Rubik's Cube Solver</h1>
        <p>
          {backendOnline === null
            ? "Connecting to solver backend…"
            : backendOnline
            ? "Backend online ✓"
            : "Backend offline — start the FastAPI server first"}
        </p>
      </header>

      {status && (
        <div className={`status-banner ${status.type}`} role="status">
          {status.type === "info" && solving && <span className="spinner" />}
          {status.msg}
        </div>
      )}

      {view === "editor" && (
        <StickerEditor
          state={cubeState}
          onChange={setCubeState}
          onSolve={handleSolve}
          onDemo={handleDemo}
          solving={solving}
          demoLoading={demoLoading}
        />
      )}

      {view === "solution" && solution && (
        <SolutionViewer
          moves={solution.moves}
          setupAlg={solution.setupAlg}
          onBack={() => setView("editor")}
        />
      )}

    </div>
  );
}
