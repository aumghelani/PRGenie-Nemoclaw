#!/usr/bin/env bash
# Fallback fast-path: Qwen3-8B on a single 16-24 GB GPU.
# Use this if Nemotron-Nano won't fit / takes too long to download.
set -euo pipefail

source "$HOME/vllm-env/bin/activate"

# Battle-plan flags: prefix caching, tool calling, JSON-friendly parser.
exec vllm serve Qwen/Qwen3-8B \
  --dtype auto \
  --trust-remote-code \
  --served-model-name agent-model \
  --host 0.0.0.0 --port 5000 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --enable-prefix-caching \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.90
