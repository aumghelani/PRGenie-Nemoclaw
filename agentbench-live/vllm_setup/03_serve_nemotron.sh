#!/usr/bin/env bash
# Recommended path: Nemotron-Nano 30B (3B active MoE) on A100 40 GB+ / H100.
# Best agentic reasoning per FLOP, native tool calling.
set -euo pipefail

source "$HOME/vllm-env/bin/activate"

export VLLM_ATTENTION_BACKEND=FLASHINFER

exec vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 \
  --dtype auto \
  --trust-remote-code \
  --served-model-name nemotron \
  --host 0.0.0.0 --port 5000 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser deepseek_r1 \
  --enable-prefix-caching \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.92
