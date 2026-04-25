#!/bin/bash
# =============================================================================
# Speed Demon — Speculative Decoding Benchmark (70B + 8B draft)
#
# Starts the 70B model with speculative decoding using 8B as draft model
# and runs throughput/latency benchmarks across all workload profiles.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VLLM_PORT="${VLLM_PORT:-8000}"
NUM_REQUESTS="${NUM_REQUESTS:-50}"
NUM_SPEC_TOKENS="${NUM_SPEC_TOKENS:-5}"
TARGET_MODEL="/models/llama-3.1-70b-instruct"
DRAFT_MODEL="/models/llama-3.1-8b-instruct"
RESULTS_DIR="${SCRIPT_DIR}/results"

mkdir -p "$RESULTS_DIR"

echo "============================================="
echo "  Speed Demon — Speculative Decoding Benchmark"
echo "  Target: Llama 3.1 70B"
echo "  Draft:  Llama 3.1 8B"
echo "  Speculative tokens: $NUM_SPEC_TOKENS"
echo "  Port: $VLLM_PORT"
echo "============================================="

# --- Start vLLM server with speculative decoding ---
echo "[1/3] Starting vLLM server (speculative)..."
python3 -m vllm.entrypoints.openai.api_server \
    --model "$TARGET_MODEL" \
    --speculative-model "$DRAFT_MODEL" \
    --num-speculative-tokens "$NUM_SPEC_TOKENS" \
    --tensor-parallel-size 2 \
    --host 0.0.0.0 \
    --port "$VLLM_PORT" \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.90 \
    --dtype auto &
SERVER_PID=$!

# Wait for server readiness
echo "  Waiting for server to be ready..."
for i in $(seq 1 180); do
    if curl -s "http://localhost:${VLLM_PORT}/health" > /dev/null 2>&1; then
        echo "  Server ready after ${i}s"
        break
    fi
    if [ "$i" -eq 180 ]; then
        echo "  ERROR: Server failed to start within 180s"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# --- Run benchmarks ---
echo "[2/3] Running benchmarks ($NUM_REQUESTS requests per workload)..."
python3 "${SCRIPT_DIR}/run_workload_bench.py" \
    --port "$VLLM_PORT" \
    --model "$TARGET_MODEL" \
    --num-requests "$NUM_REQUESTS" \
    --workloads "${SCRIPT_DIR}/workloads.json" \
    --output "${RESULTS_DIR}/speculative_k${NUM_SPEC_TOKENS}.json" \
    --tag "speculative_k${NUM_SPEC_TOKENS}"

echo "[3/3] Stopping server..."
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null || true

echo ""
echo "Speculative results saved to: ${RESULTS_DIR}/speculative_k${NUM_SPEC_TOKENS}.json"
echo "Run 'python3 plot_results.py' to generate comparison charts."
