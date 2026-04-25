#!/bin/bash
# =============================================================================
# Align It — Serve base and aligned (LoRA) models for comparison
#
# Port 8000: Base Llama 3.1 8B (unaligned)
# Port 8001: Llama 3.1 8B + DPO LoRA adapter (aligned)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_MODEL="/models/llama-3.1-8b-instruct"
LORA_PATH="${SCRIPT_DIR}/aligned-model"

if [ ! -d "$LORA_PATH" ]; then
    echo "ERROR: Aligned model not found at $LORA_PATH"
    echo "Run 'python3 train_dpo.py' first."
    exit 1
fi

echo "============================================="
echo "  Align It — Serving Base + Aligned Models"
echo "============================================="

# --- Base model (no LoRA) ---
echo "[1/2] Starting base model on port 8000..."
python3 -m vllm.entrypoints.openai.api_server \
    --model "$BASE_MODEL" \
    --host 0.0.0.0 \
    --port 8000 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.40 \
    --dtype auto &
PID_BASE=$!

# --- Aligned model (with LoRA adapter) ---
echo "[2/2] Starting aligned model on port 8001..."
python3 -m vllm.entrypoints.openai.api_server \
    --model "$BASE_MODEL" \
    --enable-lora \
    --lora-modules "aligned=${LORA_PATH}" \
    --host 0.0.0.0 \
    --port 8001 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.40 \
    --dtype auto &
PID_ALIGNED=$!

# --- Wait for both ---
echo ""
echo "Waiting for servers..."
for port in 8000 8001; do
    for i in $(seq 1 90); do
        if curl -s "http://localhost:${port}/health" > /dev/null 2>&1; then
            echo "  Port $port ready after ${i}s"
            break
        fi
        if [ "$i" -eq 90 ]; then
            echo "  ERROR: Server on port $port failed to start"
            kill $PID_BASE $PID_ALIGNED 2>/dev/null
            exit 1
        fi
        sleep 1
    done
done

echo ""
echo "============================================="
echo "  Both models serving!"
echo ""
echo "  Base (unaligned): http://localhost:8000/v1"
echo "  Aligned (DPO):    http://localhost:8001/v1"
echo "    (LoRA adapter name: 'aligned')"
echo ""
echo "  Next: python3 evaluate_alignment.py"
echo "  Press Ctrl+C to stop."
echo "============================================="

cleanup() {
    kill $PID_BASE $PID_ALIGNED 2>/dev/null
    wait $PID_BASE $PID_ALIGNED 2>/dev/null
}
trap cleanup EXIT INT TERM
wait
