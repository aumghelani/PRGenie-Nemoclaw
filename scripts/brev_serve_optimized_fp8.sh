#!/usr/bin/env bash
# Optimized mode (prefix caching ON + FP8 KV cache) for the FP8 Nemotron variant
# on 2× A100 40GB. Pair with brev_serve_baseline_fp8.sh for the before/after demo.
#
# Why these flags:
#   --tensor-parallel-size 2   use both A100s
#   --enable-prefix-caching    headline win — same SYSTEM_* prompts cached across our 4 agents
#   --kv-cache-dtype fp8       halves KV cache memory → more concurrent requests
#   --reasoning-parser deepseek_r1   parses Nemotron's <think> blocks cleanly
set -euo pipefail

source "$HOME/vllm-env/bin/activate"

# FlashInfer attention is faster on Ampere too (not just Hopper).
export VLLM_ATTENTION_BACKEND=FLASHINFER

exec vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8 \
  --dtype auto \
  --trust-remote-code \
  --served-model-name nemotron \
  --host 0.0.0.0 --port 5000 \
  --tensor-parallel-size 2 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser deepseek_r1 \
  --enable-prefix-caching \
  --kv-cache-dtype fp8 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.90
