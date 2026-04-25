// Thin client for the FastAPI backend. Vite dev server proxies /api → :8000.
const BASE = "/api";

export async function listTasks() {
  const r = await fetch(`${BASE}/tasks`);
  if (!r.ok) throw new Error(`tasks: ${r.status}`);
  return r.json();
}

export async function startRun(taskId, mode) {
  const r = await fetch(`${BASE}/benchmark/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: taskId, mode }),
  });
  if (!r.ok) throw new Error(`run: ${r.status}`);
  return r.json();
}

export async function getRun(runId) {
  const r = await fetch(`${BASE}/benchmark/${runId}`);
  if (!r.ok) throw new Error(`run: ${r.status}`);
  return r.json();
}

export function streamRun(runId, onEvent) {
  // Vite proxies /ws → ws://localhost:8000/ws
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${proto}//${window.location.host}/ws/${runId}`;
  const ws = new WebSocket(url);
  ws.onmessage = (msg) => {
    try { onEvent(JSON.parse(msg.data)); } catch (e) { console.error(e); }
  };
  ws.onerror = (e) => console.error("ws", e);
  return () => ws.close();
}
