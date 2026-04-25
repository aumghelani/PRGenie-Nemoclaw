# What is vLLM?

vLLM is a high-throughput and memory-efficient inference and serving engine for Large Language Models (LLMs). It was originally developed at UC Berkeley and is now one of the most widely-used open-source LLM serving frameworks.

## Key Features

### PagedAttention
vLLM's core innovation is PagedAttention, a novel attention algorithm inspired by virtual memory paging in operating systems. Instead of allocating a contiguous block of GPU memory for each sequence's KV-cache, PagedAttention manages memory in fixed-size blocks (pages) that can be stored non-contiguously. This reduces memory waste from internal fragmentation by up to 55%, allowing vLLM to serve significantly more concurrent sequences.

### Continuous Batching
Unlike static batching (where the server waits to fill a batch before processing), vLLM uses continuous batching (also called iteration-level scheduling). New requests are added to the running batch as soon as existing requests complete a generation step. This dramatically improves GPU utilization and reduces latency for short requests.

### Tensor Parallelism
For models too large to fit on a single GPU, vLLM supports tensor parallelism — splitting the model's weight matrices across multiple GPUs. A 70B parameter model typically requires 2-4 GPUs with tensor parallelism.

### Speculative Decoding
vLLM supports speculative decoding, where a smaller "draft" model generates candidate tokens that the larger "target" model then verifies in parallel. When the draft model's predictions are correct (which happens frequently for routine text), this can provide 2-3x speedup with no quality loss.

## OpenAI-Compatible API

vLLM exposes an OpenAI-compatible REST API, meaning any application built for the OpenAI API can switch to a local vLLM instance by simply changing the base URL. Supported endpoints include:

- `/v1/chat/completions` — Chat-style inference
- `/v1/completions` — Text completion
- `/v1/models` — List available models
- `/v1/embeddings` — Text embeddings (with supported models)

## Common Configuration Flags

- `--model`: Path to model weights or HuggingFace model ID
- `--tensor-parallel-size`: Number of GPUs for tensor parallelism
- `--max-model-len`: Maximum sequence length (prompt + generation)
- `--gpu-memory-utilization`: Fraction of GPU memory to use (default 0.90)
- `--dtype`: Data type for weights (auto, float16, bfloat16)
- `--quantization`: Quantization method (awq, gptq, squeezellm)

## Performance Tips

1. **Increase `--gpu-memory-utilization`** to 0.90-0.95 if you have no other GPU workloads
2. **Use `--max-model-len`** to limit sequence length — shorter limits use less KV-cache memory
3. **Enable speculative decoding** for latency-sensitive workloads with `--speculative-model`
4. **Use quantized models** (AWQ, GPTQ) to fit larger models on smaller GPUs
5. **Benchmark with guidellm** to measure throughput under realistic load
