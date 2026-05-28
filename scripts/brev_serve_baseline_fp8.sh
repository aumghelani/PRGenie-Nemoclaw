#!/usr/bin/env bash
# Baseline mode (prefix caching OFF) for the FP8 Nemotron variant on 2× A100 40GB.
# Pair with brev_serve_optimized_fp8.sh to produce the before/after metrics.
set -euo pipefail

source "$HOME/vllm-env/bin/activate"

exec vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8 \
  --dtype auto \
  --trust-remote-code \
  --served-model-name nemotron \
  --host 0.0.0.0 --port 5000 \
  --tensor-parallel-size 2 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --no-enable-prefix-caching \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.90
