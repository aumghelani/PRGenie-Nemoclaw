#!/bin/bash
# =============================================================================
# TOA vLLM/LLM-D Hackathon — Tier 2: Performance & Scale
# Brev Launchable Setup Script
# GPU: 2x A100 80GB or 2x H100
# Models: Llama 3.1 8B (baseline) + Llama 3.1 70B (scale target)
# =============================================================================

set -euo pipefail

echo "============================================="
echo "  TOA Hackathon — Performance Environment"
echo "  Setting up multi-GPU instance..."
echo "============================================="

# --- System basics ---
sudo apt-get update -qq
sudo apt-get install -y -qq git curl wget jq htop tmux tree nvtop

# --- Python environment ---
echo "[1/7] Setting up Python environment..."
pip install --upgrade pip --break-system-packages -q
pip install --break-system-packages -q \
    vllm \
    torch \
    transformers \
    huggingface_hub \
    guidellm \
    lm-eval \
    llmcompressor \
    auto-gptq \
    autoawq \
    trl \
    peft \
    datasets \
    jupyter \
    ipywidgets \
    pandas \
    matplotlib \
    rich \
    httpx \
    gradio \
    py-spy

# --- Download 8B model (baseline for benchmarking) ---
echo "[2/7] Downloading Llama 3.1 8B Instruct (baseline)..."
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    'meta-llama/Llama-3.1-8B-Instruct',
    local_dir='/models/llama-3.1-8b-instruct',
    ignore_patterns=['*.pth', 'original/**']
)
"

# --- Download 70B model (scale target) ---
echo "[3/7] Downloading Llama 3.1 70B Instruct..."
echo "      This will take a while (~140GB). Pre-cached for your convenience."
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    'meta-llama/Llama-3.1-70B-Instruct',
    local_dir='/models/llama-3.1-70b-instruct',
    ignore_patterns=['*.pth', 'original/**']
)
"

# --- Install llm-d components ---
echo "[4/7] Installing llm-d and Kubernetes tooling..."
# kubectl
curl -sLO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl

# Helm
curl -sfL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# kind (for local K8s cluster if needed)
curl -sLo ./kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64
sudo install -o root -g root -m 0755 kind /usr/local/bin/kind && rm kind

# Clone llm-d repo for Helm charts and examples
git clone --depth 1 https://github.com/llm-d/llm-d.git /workspace/llm-d

# --- Benchmarking scripts ---
echo "[5/7] Setting up benchmarking toolkit..."
mkdir -p /workspace/benchmarks

cat > /workspace/benchmarks/bench_throughput.sh << 'BENCH'
#!/bin/bash
# Quick throughput benchmark using vLLM's built-in benchmarking
# Usage: bash bench_throughput.sh [model_path] [num_prompts] [tensor_parallel_size]

MODEL=${1:-/models/llama-3.1-8b-instruct}
NUM_PROMPTS=${2:-100}
TP=${3:-1}

echo "Benchmarking: $MODEL"
echo "Prompts: $NUM_PROMPTS | Tensor Parallel: $TP"
echo "---"

python3 -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --tensor-parallel-size "$TP" \
    --host 0.0.0.0 --port 8000 \
    --max-model-len 4096 \
    --dtype auto &
SERVER_PID=$!

echo "Waiting for server to start..."
for i in $(seq 1 60); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "Server ready after ${i}s"
        break
    fi
    sleep 1
done

echo "Running benchmark..."
python3 -c "
import httpx, time, statistics

url = 'http://localhost:8000/v1/chat/completions'
prompts = [
    'Explain quantum computing in simple terms.',
    'Write a Python function to sort a list.',
    'What are the benefits of distributed systems?',
    'Describe the architecture of a transformer model.',
    'How does KV-cache optimization work in LLM inference?',
]

latencies = []
tokens_generated = []
for i in range($NUM_PROMPTS):
    prompt = prompts[i % len(prompts)]
    start = time.time()
    r = httpx.post(url, json={
        'model': '$MODEL',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 128,
        'temperature': 0.1
    }, timeout=120)
    elapsed = time.time() - start
    latencies.append(elapsed)
    toks = r.json()['usage']['completion_tokens']
    tokens_generated.append(toks)

total_tokens = sum(tokens_generated)
total_time = sum(latencies)
print(f'--- Results ({$NUM_PROMPTS} requests) ---')
print(f'Total tokens generated: {total_tokens}')
print(f'Total time: {total_time:.2f}s')
print(f'Throughput: {total_tokens/total_time:.1f} tokens/sec')
print(f'Avg latency: {statistics.mean(latencies)*1000:.0f}ms')
print(f'P50 latency: {statistics.median(latencies)*1000:.0f}ms')
print(f'P99 latency: {sorted(latencies)[int(0.99*len(latencies))]*1000:.0f}ms')
"

kill $SERVER_PID 2>/dev/null
BENCH
chmod +x /workspace/benchmarks/bench_throughput.sh

# --- Quantization starter script ---
cat > /workspace/benchmarks/quantize_model.py << 'QUANTIZE'
"""
Starter script: quantize Llama 3.1 8B with llm-compressor.
Modify this for Track 1 (Lean Inference Challenge).
"""
from llmcompressor.modifiers.quantization import GPTQModifier
from llmcompressor.transformers import oneshot
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_PATH = "/models/llama-3.1-8b-instruct"
OUTPUT_PATH = "/models/llama-3.1-8b-instruct-gptq-4bit"

print("Loading model...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH, device_map="auto", torch_dtype="auto"
)
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

print("Running GPTQ 4-bit quantization...")
recipe = GPTQModifier(targets="Linear", scheme="W4A16", ignore=["lm_head"])

oneshot(
    model=model,
    dataset="ultrachat_200k",
    recipe=recipe,
    output_dir=OUTPUT_PATH,
    num_calibration_samples=256,
    max_seq_length=2048,
)
print(f"Quantized model saved to {OUTPUT_PATH}")
print("Now benchmark it against the original with bench_throughput.sh!")
QUANTIZE

# --- Speculative decoding starter ---
cat > /workspace/benchmarks/speculative_decoding.sh << 'SPEC_DEC'
#!/bin/bash
# Start vLLM with speculative decoding enabled
# Uses 8B as draft model for 70B target
echo "Starting vLLM with speculative decoding..."
echo "  Target: Llama 3.1 70B | Draft: Llama 3.1 8B"
echo "  Speculation length: 5 tokens"
python3 -m vllm.entrypoints.openai.api_server \
    --model /models/llama-3.1-70b-instruct \
    --speculative-model /models/llama-3.1-8b-instruct \
    --num-speculative-tokens 5 \
    --tensor-parallel-size 2 \
    --host 0.0.0.0 --port 8000 \
    --max-model-len 4096 \
    --dtype auto
SPEC_DEC
chmod +x /workspace/benchmarks/speculative_decoding.sh

# --- Multi-GPU serving scripts ---
echo "[6/7] Setting up multi-GPU serving scripts..."
mkdir -p /workspace/serving

cat > /workspace/serving/serve_70b_tp2.sh << 'SERVE70B'
#!/bin/bash
# Serve Llama 3.1 70B with tensor parallelism across 2 GPUs
echo "Starting Llama 3.1 70B on 2 GPUs (tensor parallel)..."
python3 -m vllm.entrypoints.openai.api_server \
    --model /models/llama-3.1-70b-instruct \
    --tensor-parallel-size 2 \
    --host 0.0.0.0 --port 8000 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.90 \
    --dtype auto
SERVE70B
chmod +x /workspace/serving/serve_70b_tp2.sh

cat > /workspace/serving/serve_8b_baseline.sh << 'SERVE8B'
#!/bin/bash
# Serve 8B as a baseline for comparison
echo "Starting Llama 3.1 8B baseline (single GPU)..."
python3 -m vllm.entrypoints.openai.api_server \
    --model /models/llama-3.1-8b-instruct \
    --host 0.0.0.0 --port 8000 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.85 \
    --dtype auto
SERVE8B
chmod +x /workspace/serving/serve_8b_baseline.sh

# --- Environment validation ---
echo "[7/7] Creating environment validation script..."
cat > /workspace/test_setup.sh << 'VALIDATE'
#!/bin/bash
echo "============================================="
echo "  Performance Environment Validation"
echo "============================================="
PASS=0; FAIL=0

check() {
    if eval "$2" > /dev/null 2>&1; then
        echo "  ✓ $1"; ((PASS++))
    else
        echo "  ✗ $1"; ((FAIL++))
    fi
}

GPU_COUNT=$(nvidia-smi -L 2>/dev/null | wc -l)
echo "  GPUs detected: $GPU_COUNT"
echo ""

check "NVIDIA GPUs detected"           "nvidia-smi"
check "Multiple GPUs available"         "[ $GPU_COUNT -ge 2 ]"
check "CUDA available"                  "python3 -c 'import torch; assert torch.cuda.is_available()'"
check "vLLM installed"                  "python3 -c 'import vllm'"
check "8B model weights present"        "test -d /models/llama-3.1-8b-instruct"
check "70B model weights present"       "test -d /models/llama-3.1-70b-instruct"
check "guidellm installed"              "python3 -c 'import guidellm'"
check "llm-compressor installed"        "python3 -c 'import llmcompressor'"
check "TRL installed"                   "python3 -c 'import trl'"
check "PEFT installed"                  "python3 -c 'import peft'"
check "AutoAWQ installed"               "python3 -c 'import awq'"
check "kubectl installed"               "kubectl version --client"
check "Helm installed"                  "helm version"
check "llm-d repo cloned"              "test -d /workspace/llm-d"

echo "---------------------------------------------"
echo "  Results: $PASS passed, $FAIL failed"
if [ $FAIL -eq 0 ]; then
    echo "  🎉 All checks passed — you're ready to hack!"
else
    echo "  ⚠  Some checks failed. Ask a mentor for help."
fi
echo "============================================="
VALIDATE
chmod +x /workspace/test_setup.sh

# --- Final summary ---
echo ""
echo "============================================="
echo "  ✅ Performance environment ready!"
echo ""
echo "  Quick start:"
echo "    1. bash /workspace/test_setup.sh"
echo "    2. bash /workspace/serving/serve_8b_baseline.sh"
echo "    3. bash /workspace/benchmarks/bench_throughput.sh"
echo ""
echo "  Models:"
echo "    /models/llama-3.1-8b-instruct   (baseline)"
echo "    /models/llama-3.1-70b-instruct   (scale target)"
echo ""
echo "  Tracks:"
echo "    Quantization:  python3 /workspace/benchmarks/quantize_model.py"
echo "    Spec decode:   bash /workspace/benchmarks/speculative_decoding.sh"
echo "    70B serving:   bash /workspace/serving/serve_70b_tp2.sh"
echo "    llm-d:         see /workspace/llm-d/ for Helm charts"
echo "============================================="
