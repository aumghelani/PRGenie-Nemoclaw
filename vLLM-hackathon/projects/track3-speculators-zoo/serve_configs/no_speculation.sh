#!/bin/bash
# Baseline — no speculation. For comparison.
python3 -m vllm.entrypoints.openai.api_server \
    --model /models/llama-3.1-70b-instruct \
    --tensor-parallel-size 2 \
    --host 0.0.0.0 --port 8000 \
    --max-model-len 4096 \
    --dtype auto
