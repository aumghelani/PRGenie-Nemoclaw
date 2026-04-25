# TOA vLLM Hackathon — FAQ

## General

### When and where is the hackathon?
The hackathon takes place on April 25, 2026 at The Open Accelerator in the Fortpoint neighborhood of Boston, Massachusetts.

### What should I bring?
Bring your laptop, charger, and any peripherals you prefer. All heavy compute runs on cloud GPU instances — you don't need a powerful local machine.

### Do I need prior experience with LLMs?
No. The hackathon is designed for all skill levels. Tier 1 (App Builder) is specifically tailored for newcomers who want to build applications on top of LLMs without needing to understand the internals. Mentors from the vLLM and llm-d teams will be available throughout the event.

## Compute & Models

### What GPU instances are available?
Three tiers of pre-configured NVIDIA Brev instances:
- **Tier 1:** 1x L40S (48 GB VRAM) — for app builders and RAG projects
- **Tier 2:** 2x A100 (80 GB each) — for performance tuning and speculative decoding
- **Tier 3:** 4x A100 (80 GB each) — for distributed inference and Kubernetes-based deployments

### Which models are pre-loaded?
- **Llama 3.1 8B Instruct** is available on all tiers
- **Llama 3.1 70B Instruct** is additionally available on Tier 2 and Tier 3
- A small embedding model (**BGE-small-en-v1.5**) is available on Tier 1 for RAG use cases

### Can I use my own model?
Yes. You can download any HuggingFace model onto your instance. Just be mindful of VRAM — the 8B model uses roughly 16 GB in float16, and the 70B model uses roughly 140 GB.

### How do I access the LLM?
All models are served via vLLM, which provides an OpenAI-compatible API at `http://localhost:8000/v1`. You can use the OpenAI Python SDK, LangChain, cURL, or any HTTP client.

## Tracks

### What are the hackathon tracks?
1. **Lean Inference Challenge** — Quantize models and optimize throughput
2. **RAG on Open Inference** — Build retrieval-augmented apps with vLLM
3. **Speculative Futures** — Accelerate inference with draft model speculation
4. **Inference at Scale** — Deploy distributed inference with llm-d on Kubernetes
5. **BYOP (Build Your Own Product)** — Ship a product powered by open-source LLMs
6. **Performance Tuning & Evaluation** — Benchmark and optimize with guidellm / lm-eval

### Can I switch tracks mid-hackathon?
Yes. Tracks are suggestions, not restrictions. You can combine ideas from multiple tracks.

## Tools & Frameworks

### What is llm-d?
llm-d is a distributed inference framework that extends vLLM across Kubernetes clusters. It supports disaggregated serving (running prefill and decode phases on separate GPU pools) and KV-cache-aware request routing for optimal resource utilization.

### What is ZeroClaw?
ZeroClaw is a code assistant demo included in the hackathon repo. It routes simple code tasks (explain, refactor, review) to a local quantized LLM and complex tasks (architecture, security) to a cloud model. It demonstrates hybrid local/cloud inference patterns.

### What evaluation tools are available?
- **guidellm** — Load testing and throughput/latency measurement for LLM APIs
- **lm-eval** — Academic benchmark suites (HellaSwag, ARC, MMLU, etc.)
- **nvtop** — Real-time GPU utilization monitoring
- **py-spy** — Python profiler for CPU-side bottleneck analysis
