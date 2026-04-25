#!/usr/bin/env bash
# Baseline mode for the demo: prefix caching + spec decoding OFF, FP8 OFF.
# Pair with 04_serve_optimized.sh to produce the before/after metrics.
set -euo pipefail

source "$HOME/vllm-env/bin/activate"

exec vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 \
  --dtype auto \
  --trust-remote-code \
  --served-model-name nemotron \
  --host 0.0.0.0 --port 5000 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --no-enable-prefix-caching \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.92
