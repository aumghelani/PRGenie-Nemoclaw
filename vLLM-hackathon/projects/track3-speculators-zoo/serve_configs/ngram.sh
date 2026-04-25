#!/bin/bash
# N-gram speculation: no draft model — speculate from observed token n-grams.
# Cheapest option. Works well when generation is repetitive (code, structured output).
python3 -m vllm.entrypoints.openai.api_server \
    --model /models/llama-3.1-70b-instruct \
    --speculative-model "[ngram]" \
    --ngram-prompt-lookup-max 4 \
    --ngram-prompt-lookup-min 2 \
    --num-speculative-tokens 5 \
    --tensor-parallel-size 2 \
    --host 0.0.0.0 --port 8000 \
    --max-model-len 4096 \
    --dtype auto
