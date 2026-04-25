#!/bin/bash
# Medusa speculation: multiple independent draft heads added to the target model.
# More memory than EAGLE, but can speculate multiple future positions in parallel.
python3 -m vllm.entrypoints.openai.api_server \
    --model /models/llama-3.1-70b-instruct \
    --speculative-model /models/medusa-llama-3.1-70b \
    --speculative-model-type medusa \
    --num-speculative-tokens 4 \
    --tensor-parallel-size 2 \
    --host 0.0.0.0 --port 8000 \
    --max-model-len 4096 \
    --dtype auto
