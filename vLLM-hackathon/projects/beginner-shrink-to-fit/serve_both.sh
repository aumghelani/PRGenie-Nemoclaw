#!/bin/bash
# =============================================================================
# Shrink to Fit — Serve both full-precision and quantized models
#
# Launches two vLLM instances:
#   Port 8000: Full Llama 3.1 8B (FP16) — baseline
#   Port 8001: Llama 3.1 8B AWQ (INT4)  — quantized
#
# Both run on the same GPU — the quantized model uses much less VRAM.
# =============================================================================

set -euo pipefail

FULL_MODEL="/models/llama-3.1-8b-instruct"
QUANT_MODEL="/models/llama-3.1-8b-instruct-awq-int4"

if [ ! -d "$QUANT_MODEL" ]; then
    echo "ERROR: Quantized model not found at $QUANT_MODEL"
    echo "Run 'python3 download_quantized.py' first."
    exit 1
fi

echo "============================================="
echo "  Shrink to Fit — Serving Both Models"
echo "============================================="
echo ""

# --- Start full-precision model ---
echo "[1/2] Starting full-precision model on port 8000..."
python3 -m vllm.entrypoints.openai.api_server \
    --model "$FULL_MODEL" \
    --host 0.0.0.0 \
    --port 8000 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.45 \
    --dtype auto &
PID_FULL=$!

# --- Start quantized model ---
echo "[2/2] Starting quantized model on port 8001..."
python3 -m vllm.entrypoints.openai.api_server \
    --model "$QUANT_MODEL" \
    --host 0.0.0.0 \
    --port 8001 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.45 \
    --quantization awq \
    --dtype auto &
PID_QUANT=$!

# --- Wait for both to be ready ---
echo ""
echo "Waiting for servers to start..."
for port in 8000 8001; do
    for i in $(seq 1 90); do
        if curl -s "http://localhost:${port}/health" > /dev/null 2>&1; then
            echo "  Port $port ready after ${i}s"
            break
        fi
        if [ "$i" -eq 90 ]; then
            echo "  ERROR: Server on port $port failed to start"
            kill $PID_FULL $PID_QUANT 2>/dev/null
            exit 1
        fi
        sleep 1
    done
done

echo ""
echo "============================================="
echo "  Both models serving!"
echo ""
echo "  Full (FP16):     http://localhost:8000/v1"
echo "  Quantized (AWQ): http://localhost:8001/v1"
echo ""
echo "  Next: python3 compare_app.py"
echo "  Or:   python3 benchmark_both.py"
echo ""
echo "  Press Ctrl+C to stop both servers."
echo "============================================="

# Wait for either to exit
cleanup() {
    echo "Stopping servers..."
    kill $PID_FULL $PID_QUANT 2>/dev/null
    wait $PID_FULL $PID_QUANT 2>/dev/null
}
trap cleanup EXIT INT TERM
wait
