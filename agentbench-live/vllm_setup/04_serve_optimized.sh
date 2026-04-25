#!/usr/bin/env bash
# Full-throttle: Nemotron + FP8 KV cache + speculative decoding (EAGLE-3).
# This is the "optimized" mode for the AgentBench Live demo — it pairs with
# 03_serve_nemotron.sh as the "baseline" and produces the before/after delta.
set -euo pipefail

source "$HOME/vllm-env/bin/activate"

export VLLM_ATTENTION_BACKEND=FLASHINFER

# Optional: point at an EAGLE-3 draft from RedHatAI's HF collection.
# huggingface-cli download RedHatAI/eagle3-nemotron-nano-3-30b --local-dir /tmp/eagle3-draft
DRAFT_MODEL="${DRAFT_MODEL:-}"

ARGS=(
  vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16
  --dtype auto
  --trust-remote-code
  --served-model-name nemotron
  --host 0.0.0.0 --port 5000
  --enable-auto-tool-choice
  --tool-call-parser qwen3_coder
  --reasoning-parser deepseek_r1
  --enable-prefix-caching
  --kv-cache-dtype fp8
  --max-model-len 32768
  --gpu-memory-utilization 0.92
)

if [ -n "$DRAFT_MODEL" ]; then
  ARGS+=(--speculative-model "$DRAFT_MODEL" --num-speculative-tokens 5)
fi

exec "${ARGS[@]}"
