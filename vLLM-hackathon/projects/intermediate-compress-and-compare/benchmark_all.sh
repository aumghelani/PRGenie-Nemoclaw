#!/bin/bash
# =============================================================================
# Compress & Compare — Throughput Benchmark for All Model Variants
#
# Benchmarks each quantized variant by starting a vLLM server, running a
# throughput test, recording the results, and shutting down before the next.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
NUM_REQUESTS="${NUM_REQUESTS:-30}"
PORT=8000

mkdir -p "$RESULTS_DIR"

# Build model list dynamically
declare -A MODELS
MODELS[original]="/models/llama-3.1-8b-instruct"
QUANT_ARGS=""

if [ -d "/models/llama-3.1-8b-instruct-gptq-4bit" ]; then
    MODELS[gptq_4bit]="/models/llama-3.1-8b-instruct-gptq-4bit"
fi
if [ -d "/models/llama-3.1-8b-instruct-awq-4bit" ]; then
    MODELS[awq_4bit]="/models/llama-3.1-8b-instruct-awq-4bit"
fi

echo "============================================="
echo "  Compress & Compare — Throughput Benchmarks"
echo "  Models: ${!MODELS[*]}"
echo "  Requests per model: $NUM_REQUESTS"
echo "============================================="

PROMPTS='[
  "Explain how a neural network learns through backpropagation.",
  "Write a Python function that implements quicksort.",
  "What are the key differences between SQL and NoSQL databases?",
  "Describe the architecture of a modern web browser.",
  "Explain the concept of eventual consistency in distributed systems."
]'

for variant in "${!MODELS[@]}"; do
    model_path="${MODELS[$variant]}"
    echo ""
    echo "--- Benchmarking: $variant ($model_path) ---"

    # Determine if we need quantization flag
    EXTRA_ARGS=""
    if [[ "$variant" == *"gptq"* ]]; then
        EXTRA_ARGS="--quantization gptq"
    elif [[ "$variant" == *"awq"* ]]; then
        EXTRA_ARGS="--quantization awq"
    fi

    # Start server
    echo "  Starting vLLM server..."
    python3 -m vllm.entrypoints.openai.api_server \
        --model "$model_path" \
        --host 0.0.0.0 \
        --port $PORT \
        --max-model-len 4096 \
        --gpu-memory-utilization 0.85 \
        --dtype auto \
        $EXTRA_ARGS &
    SERVER_PID=$!

    # Wait for ready
    for i in $(seq 1 90); do
        if curl -s "http://localhost:${PORT}/health" > /dev/null 2>&1; then
            echo "  Server ready after ${i}s"
            break
        fi
        if [ "$i" -eq 90 ]; then
            echo "  ERROR: Server failed to start"
            kill $SERVER_PID 2>/dev/null; wait $SERVER_PID 2>/dev/null || true
            continue 2
        fi
        sleep 1
    done

    # Record GPU memory
    GPU_MEM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    echo "  GPU memory used: ${GPU_MEM} MB"

    # Run benchmark
    python3 -c "
import httpx, time, statistics, json

url = 'http://localhost:${PORT}/v1/chat/completions'
model = '${model_path}'
prompts = ${PROMPTS}
num_requests = ${NUM_REQUESTS}

latencies = []
tokens_list = []
for i in range(num_requests):
    prompt = prompts[i % len(prompts)]
    start = time.perf_counter()
    r = httpx.post(url, json={
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 128,
        'temperature': 0.1,
    }, timeout=120)
    elapsed = time.perf_counter() - start
    latencies.append(elapsed)
    tokens_list.append(r.json()['usage']['completion_tokens'])

total_tokens = sum(tokens_list)
total_time = sum(latencies)
result = {
    'variant': '${variant}',
    'model': model,
    'gpu_memory_mb': ${GPU_MEM},
    'num_requests': num_requests,
    'total_tokens': total_tokens,
    'throughput_tps': total_tokens / total_time,
    'latency_mean_ms': statistics.mean(latencies) * 1000,
    'latency_median_ms': statistics.median(latencies) * 1000,
    'latency_p95_ms': sorted(latencies)[int(0.95 * len(latencies))] * 1000,
}

print(f'  Throughput: {result[\"throughput_tps\"]:.1f} tok/s')
print(f'  Latency (median): {result[\"latency_median_ms\"]:.0f} ms')
print(f'  VRAM: {result[\"gpu_memory_mb\"]} MB')

with open('${RESULTS_DIR}/bench_${variant}.json', 'w') as f:
    json.dump(result, f, indent=2)
"

    # Stop server
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null || true
    sleep 3  # Let GPU memory clear
done

echo ""
echo "============================================="
echo "  Benchmarks complete!"
echo "  Results: ${RESULTS_DIR}/bench_*.json"
echo ""
echo "  Next: python3 plot_tradeoffs.py"
echo "============================================="
