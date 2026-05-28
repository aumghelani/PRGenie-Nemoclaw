#!/usr/bin/env bash
# Optimized mode (prefix caching + FP8 KV cache + FlashInfer) for Nemotron-Nano-30B
# BF16 on 2× A100 40GB. Pair with brev_serve_baseline_bf16_2gpu.sh for the
# before/after demo.
#
# Why these flags matter for the Track 5 score:
#   --enable-prefix-caching     same SYSTEM_TRIAGE / SYSTEM_PERSONA / SYSTEM_REVIEW
#                               prompts get re-used → cache hit on every call after #1
#   --kv-cache-dtype fp8        halves KV cache memory → fits more concurrent reqs +
#                               longer context. Recovers most of the memory pressure
#                               from running BF16 weights on 2× A100 40GB.
#   --tensor-parallel-size 2    use both GPUs (otherwise GPU 1 sits idle)
#   VLLM_ATTENTION_BACKEND=FLASHINFER   faster attention kernel on Ampere
set -euo pipefail

source "$HOME/vllm-env/bin/activate"

export VLLM_ATTENTION_BACKEND=FLASHINFER

exec vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 \
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
  --max-model-len 16384 \
  --gpu-memory-utilization 0.92
