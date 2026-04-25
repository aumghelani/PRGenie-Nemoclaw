#!/usr/bin/env bash
# Boots a tiny model and hits /v1/completions to verify the install.
set -euo pipefail

source "$HOME/vllm-env/bin/activate"

MODEL="${MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"
PORT="${PORT:-5000}"

echo "[smoke] Booting $MODEL on port $PORT in background…"
vllm serve "$MODEL" \
  --host 0.0.0.0 --port "$PORT" \
  --max-model-len 4096 \
  --enable-prefix-caching \
  --gpu-memory-utilization 0.5 \
  > /tmp/vllm-smoke.log 2>&1 &

VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT

echo "[smoke] Waiting up to 120 s for server…"
for i in $(seq 1 120); do
  if curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1; then
    echo "[smoke] Server up after ${i}s"
    break
  fi
  sleep 1
done

echo "[smoke] /v1/models response:"
curl -s "http://localhost:$PORT/v1/models" | head -c 500
echo

echo
echo "[smoke] /v1/completions test:"
curl -s "http://localhost:$PORT/v1/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"prompt\":\"Hello, vLLM!\",\"max_tokens\":20}" \
  | head -c 1000
echo

echo
echo "[smoke] PASS — vLLM is alive."
echo "[smoke] Killing background server (PID $VLLM_PID)…"
