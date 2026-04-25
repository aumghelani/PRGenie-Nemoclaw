#!/bin/bash
# Draft-model speculation: Llama 3.1 8B drafts for Llama 3.1 70B.
# Classic vLLM spec-decode. ~1.8× speedup typical.
python3 -m vllm.entrypoints.openai.api_server \
    --model /models/llama-3.1-70b-instruct \
    --speculative-model /models/llama-3.1-8b-instruct \
    --num-speculative-tokens 5 \
    --tensor-parallel-size 2 \
    --host 0.0.0.0 --port 8000 \
    --max-model-len 4096 \
    --dtype auto
