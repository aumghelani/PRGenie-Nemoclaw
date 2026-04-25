#!/usr/bin/env bash
# Baseline mode (prefix caching OFF) for Nemotron-Nano-30B BF16 on 2× A100 40GB.
# Splits the 60GB model ~30GB per GPU via tensor parallelism.
# Pair with brev_serve_optimized_bf16_2gpu.sh for the before/after demo.
set -euo pipefail

source "$HOME/vllm-env/bin/activate"

exec vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 \
  --dtype auto \
  --trust-remote-code \
  --served-model-name nemotron \
  --host 0.0.0.0 --port 5000 \
  --tensor-parallel-size 2 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --no-enable-prefix-caching \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.92
