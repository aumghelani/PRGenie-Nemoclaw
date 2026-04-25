#!/bin/bash
# =============================================================================
# Speed Demon — Baseline Benchmark (70B without speculative decoding)
#
# Starts the 70B model with tensor parallelism and runs throughput/latency
# benchmarks across all workload profiles.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VLLM_PORT="${VLLM_PORT:-8000}"
NUM_REQUESTS="${NUM_REQUESTS:-50}"
MODEL="/models/llama-3.1-70b-instruct"
RESULTS_DIR="${SCRIPT_DIR}/results"

mkdir -p "$RESULTS_DIR"

echo "============================================="
echo "  Speed Demon — Baseline Benchmark"
echo "  Model: Llama 3.1 70B (no speculation)"
echo "  Tensor Parallel: 2 GPUs"
echo "  Port: $VLLM_PORT"
echo "============================================="

# --- Start vLLM server ---
echo "[1/3] Starting vLLM server (baseline)..."
python3 -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --tensor-parallel-size 2 \
    --host 0.0.0.0 \
    --port "$VLLM_PORT" \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.90 \
    --dtype auto &
SERVER_PID=$!

# Wait for server readiness
echo "  Waiting for server to be ready..."
for i in $(seq 1 120); do
    if curl -s "http://localhost:${VLLM_PORT}/health" > /dev/null 2>&1; then
        echo "  Server ready after ${i}s"
        break
    fi
    if [ "$i" -eq 120 ]; then
        echo "  ERROR: Server failed to start within 120s"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# --- Run benchmarks ---
echo "[2/3] Running benchmarks ($NUM_REQUESTS requests per workload)..."
python3 "${SCRIPT_DIR}/run_workload_bench.py" \
    --port "$VLLM_PORT" \
    --model "$MODEL" \
    --num-requests "$NUM_REQUESTS" \
    --workloads "${SCRIPT_DIR}/workloads.json" \
    --output "${RESULTS_DIR}/baseline.json" \
    --tag "baseline"

echo "[3/3] Stopping server..."
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null || true

echo ""
echo "Baseline results saved to: ${RESULTS_DIR}/baseline.json"
echo "Run benchmark_speculative.sh next for comparison."
