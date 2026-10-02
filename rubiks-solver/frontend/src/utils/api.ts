import type { SolveResponse, DemoResponse } from "../types/cube";

// In production on Vercel, requests to /api/* are rewritten to the backend service.
// In local dev, Vite proxies /api/* to http://localhost:8000/api.
// Can also be overridden with VITE_API_URL if connecting directly to an external backend.
const API = import.meta.env.VITE_API_URL ?? "/api";

export async function solveCube(stateArr: string[]): Promise<SolveResponse> {
  const res = await fetch(`${API}/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state: stateArr }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Solve failed");
  }
  return res.json();
}

export async function fetchDemo(): Promise<DemoResponse> {
  const res = await fetch(`${API}/demo`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Demo failed");
  }
  return res.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API}/health`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}
