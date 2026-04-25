#!/bin/bash
# EAGLE speculation on Llama 3.1 70B.
# EAGLE trains lightweight draft heads that share the target's embedding space,
# giving higher acceptance rates than a generic draft model.
python3 -m vllm.entrypoints.openai.api_server \
    --model /models/llama-3.1-70b-instruct \
    --speculative-model /models/eagle-llama-3.1-70b \
    --speculative-model-type eagle \
    --num-speculative-tokens 5 \
    --tensor-parallel-size 2 \
    --host 0.0.0.0 --port 8000 \
    --max-model-len 4096 \
    --dtype auto
