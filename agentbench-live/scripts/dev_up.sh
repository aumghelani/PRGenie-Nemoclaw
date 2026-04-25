#!/usr/bin/env bash
# Start FastAPI backend + Vite dev server (Linux / WSL).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Activate venv if present
if [ -f ".venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
  # shellcheck source=/dev/null
  source .venv/Scripts/activate
fi

(cd "$ROOT" && uvicorn api_server.main:app --reload --port 8000) &
BACKEND_PID=$!

(cd "$ROOT/dashboard" && npm run dev) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' EXIT

echo "API:       http://localhost:8000"
echo "Dashboard: http://localhost:5173"

wait
