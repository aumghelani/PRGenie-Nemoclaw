# Hackathon Projects Overview

A quick guide to every starter project in this directory. Pick one based on
the topic that excites you and the level that matches your experience.

---

## How to Choose

```
 What interests you?
       |
       +-- "I want to build an app"         --> RAG & Apps
       +-- "I want to make models smaller"  --> Quantization
       +-- "I want to teach a model"        --> Reinforcement Learning
       +-- "I want to scale infrastructure" --> Distributed Inference (advanced)

 What's your experience level?
       |
       +-- "New to LLMs / Python basics"    --> Beginner project
       +-- "Comfortable with ML / systems"  --> Intermediate project
```

---

## Projects at a Glance

| # | Project | Topic | Level | Tier / GPU | Time Estimate |
|---|---------|-------|-------|------------|---------------|
| 1 | [Ask My Docs](#1-ask-my-docs) | RAG & Apps | Beginner | Tier 1 · 1× L40S | 2-3 hours |
| 2 | [Shrink to Fit](#2-shrink-to-fit) | Quantization | Beginner | Tier 1 · 1× L40S | 1-2 hours |
| 3 | [Reward Ranker](#3-reward-ranker) | Reinforcement Learning | Beginner | Tier 1 · 1× L40S | 2-3 hours |
| 4 | [Speed Demon](#4-speed-demon) | RAG & Apps | Intermediate | Tier 2 · 2× A100 | 3-4 hours |
| 5 | [Compress & Compare](#5-compress--compare) | Quantization | Intermediate | Tier 2 · 2× A100 | 3-4 hours |
| 6 | [Align It](#6-align-it) | Reinforcement Learning | Intermediate | Tier 2 · 2× A100 | 3-4 hours |
| 7 | [Infinite Scale](#7-infinite-scale) | Distributed Inference | Advanced | Tier 3 · 4× A100 | 4-5 hours |

---

## Beginner Projects

These require only Python knowledge and basic familiarity with REST APIs.
Everything is pre-installed on your Brev instance — just follow the README.

### 1. Ask My Docs

**Directory:** [`beginner-ask-my-docs/`](beginner-ask-my-docs/)
**Topic:** RAG & Application Building
**Tier:** 1 — App Builder (1× L40S, 48 GB)

#### What You'll Do

Build a document Q&A application powered by Retrieval-Augmented Generation.
Upload your own files, ask questions in natural language, and get answers
grounded in your documents.

#### Goals

- Ingest documents into a ChromaDB vector store with BGE embeddings
- Build a retrieval pipeline that finds the most relevant document chunks
- Connect the pipeline to Llama 3.1 8B via vLLM's OpenAI-compatible API
- Wrap everything in a Gradio web UI

#### What You'll Learn

- How RAG works (embed → store → retrieve → generate)
- Using vLLM as a drop-in OpenAI API replacement
- Working with vector databases (ChromaDB)
- Building interactive ML apps with Gradio

#### Outcomes

- A working web app you can demo to judges
- Hands-on experience with the most common LLM application pattern
- Understanding of how enterprise knowledge bases and chatbots are built

#### Quick Start

```bash
bash /workspace/start_vllm_server.sh
cd projects/beginner-ask-my-docs
python3 ingest.py && python3 app.py
# Open http://localhost:7860
```

---

### 2. Shrink to Fit

**Directory:** [`beginner-shrink-to-fit/`](beginner-shrink-to-fit/)
**Topic:** Quantization (Model Compression)
**Tier:** 1 — App Builder (1× L40S, 48 GB)

#### What You'll Do

Compare a full-precision (16-bit, ~16 GB) model against a quantized (4-bit,
~4 GB) version side-by-side. See for yourself that a 4x smaller model
produces nearly identical quality at higher speed.

#### Goals

- Download a pre-quantized AWQ model from HuggingFace
- Serve both the original and quantized models simultaneously on one GPU
- Compare quality, speed, and VRAM usage in an interactive Gradio app
- Run an automated benchmark to quantify the differences

#### What You'll Learn

- What quantization is and why it matters for LLM deployment
- The difference between full precision (FP16) and 4-bit integer (INT4)
- How to serve quantized models with vLLM
- How to measure inference speed and memory usage

#### Outcomes

- A side-by-side comparison app showing quantization trade-offs
- Benchmark data (throughput, latency, VRAM) you can present
- Understanding of how companies deploy LLMs cost-effectively

#### Quick Start

```bash
cd projects/beginner-shrink-to-fit
python3 download_quantized.py
bash serve_both.sh
# In a new terminal:
python3 compare_app.py
# Open http://localhost:7860
```

---

### 3. Reward Ranker

**Directory:** [`beginner-reward-ranker/`](beginner-reward-ranker/)
**Topic:** Reinforcement Learning (RLHF)
**Tier:** 1 — App Builder (1× L40S, 48 GB)

#### What You'll Do

Play "AI judge": the LLM generates two responses to the same prompt, and
you pick the better one. Your preferences are collected into a dataset that
trains a **reward model** — the foundation of how ChatGPT, Claude, and every
modern chat model is aligned with human values.

#### Goals

- Generate response pairs at different temperatures (focused vs. creative)
- Collect at least 20-30 preference judgments via a Gradio ranking app
- Train a reward model that predicts human preferences using TRL
- Use the trained model to automatically score new responses

#### What You'll Learn

- What RLHF (Reinforcement Learning from Human Feedback) is
- How preference data is collected at scale
- How reward models learn to distinguish good from bad responses
- The role of temperature in controlling LLM output diversity

#### Outcomes

- A trained reward model that reflects your quality preferences
- A preference dataset you can reuse for DPO training (see Align It)
- Understanding of the alignment pipeline used by major AI labs

#### Quick Start

```bash
bash /workspace/start_vllm_server.sh
cd projects/beginner-reward-ranker
python3 collect_preferences.py    # Rank pairs at http://localhost:7860
python3 train_reward_model.py     # Train on your preferences
python3 score_responses.py        # See the model score new responses
```

---

## Intermediate Projects

These require comfort with Python, ML concepts, and working with GPUs.
They involve longer-running experiments and produce quantitative results.

### 4. Speed Demon

**Directory:** [`intermediate-speed-demon/`](intermediate-speed-demon/)
**Topic:** Speculative Decoding & Performance Tuning
**Tier:** 2 — Performance (2× A100, 80 GB each)

#### What You'll Do

Benchmark Llama 3.1 70B with and without speculative decoding (using the 8B
model as a "draft" that proposes tokens the 70B verifies in bulk). Sweep key
parameters and produce charts showing latency vs. throughput trade-offs.

#### Goals

- Serve Llama 70B across 2 GPUs with tensor parallelism
- Run baseline benchmarks (no speculation) across multiple workload profiles
- Enable speculative decoding with the 8B draft model
- Sweep `--num-speculative-tokens` from 1-9 and measure the impact
- Generate comparison charts (bar plots, sweep lines, latency distributions)

#### What You'll Learn

- How speculative decoding works (draft/verify cycle, acceptance rate)
- Tensor parallelism for multi-GPU serving
- Performance benchmarking methodology for LLM inference
- How workload characteristics (short chat vs. long generation) affect speedup

#### Outcomes

- A complete benchmark suite with automated data collection
- Publication-quality charts comparing configurations
- Quantitative understanding of when speculation helps (and when it doesn't)

#### Quick Start

```bash
cd projects/intermediate-speed-demon
bash run_benchmark_suite.sh       # Full pipeline: baseline → speculative → charts
# Or sweep speculation depth:
python3 sweep_spec_tokens.py && python3 plot_results.py
```

---

### 5. Compress & Compare

**Directory:** [`intermediate-compress-and-compare/`](intermediate-compress-and-compare/)
**Topic:** Quantization (Model Compression)
**Tier:** 2 — Performance (2× A100, 80 GB each)

#### What You'll Do

Go beyond pre-quantized models — run the quantization process yourself with
both GPTQ and AWQ methods, then measure the quality vs. speed trade-off
using academic benchmarks and throughput tests.

#### Goals

- Run GPTQ 4-bit quantization with llm-compressor (calibration-based)
- Run AWQ 4-bit quantization with AutoAWQ (activation-aware)
- Evaluate quality loss with lm-eval benchmarks (HellaSwag, ARC-Easy)
- Benchmark throughput and VRAM for all variants (original, GPTQ, AWQ)
- Generate a Pareto frontier chart (quality vs. speed)

#### What You'll Learn

- How GPTQ and AWQ quantization algorithms work internally
- The role of calibration data in post-training quantization
- How to measure quality degradation systematically
- Where each method sits on the quality-speed Pareto frontier

#### Outcomes

- Two independently quantized model variants you created
- Quality benchmark scores showing exact degradation per method
- A Pareto chart that clearly communicates the trade-off to stakeholders
- Hands-on experience with production-grade model optimization tools

#### Quick Start

```bash
cd projects/intermediate-compress-and-compare
python3 quantize_gptq.py         # ~20 min
python3 quantize_awq.py          # ~15 min
bash evaluate_quality.sh          # lm-eval benchmarks
bash benchmark_all.sh             # Throughput benchmarks
python3 plot_tradeoffs.py         # Generate charts
```

---

### 6. Align It

**Directory:** [`intermediate-align-it/`](intermediate-align-it/)
**Topic:** Reinforcement Learning (DPO)
**Tier:** 2 — Performance (2× A100, 80 GB each)

#### What You'll Do

Actually **change a model's behavior** using Direct Preference Optimization
(DPO). Generate preference data, fine-tune Llama 3.1 8B with LoRA adapters
(only ~100 MB, not 16 GB), serve the aligned model, and measure the
improvement.

#### Goals

- Generate a preference dataset by sampling the base model at different temperatures
- Run DPO training with LoRA (memory-efficient, trains ~0.5% of parameters)
- Serve both the base and aligned models for side-by-side comparison
- Evaluate alignment improvement with automated quality scoring

#### What You'll Learn

- How DPO works (direct policy optimization from preference pairs)
- What LoRA is and why it makes fine-tuning practical on limited hardware
- The role of the beta parameter in controlling alignment strength
- How to evaluate alignment quality (win rate, quality heuristics)

#### Outcomes

- A LoRA adapter (~50-100 MB) that measurably changes model behavior
- Before/after evaluation showing win rate improvement
- Understanding of the technique companies use to customize LLMs
- Experience with the TRL + PEFT training stack

#### Quick Start

```bash
cd projects/intermediate-align-it
python3 generate_preferences.py   # Create preference pairs
python3 train_dpo.py              # DPO training with LoRA (~20-40 min)
bash serve_aligned.sh             # Serve base + aligned
python3 evaluate_alignment.py     # Measure improvement
```

---

## Advanced Project (Aspirational)

This project requires prior experience with Kubernetes and distributed systems.
It is optional — recommended only for teams who finish another project early
or have strong infrastructure backgrounds.

### 7. Infinite Scale

**Directory:** [`advanced-infinite-scale/`](advanced-infinite-scale/)
**Topic:** Distributed Inference (llm-d on Kubernetes)
**Tier:** 3 — Deep Tech (4× A100, 80 GB each)

#### What You'll Do

Deploy a disaggregated inference system on Kubernetes where the prefill and
decode phases run on separate GPU pools, connected by KV-cache-aware routing.
Configure autoscaling based on real-time Prometheus metrics.

#### Goals

- Stand up a kind Kubernetes cluster with GPU passthrough
- Deploy llm-d with Helm using the disaggregated serving configuration
- Configure HorizontalPodAutoscalers for prefill and decode pools
- Run a ramping load test and observe autoscaling behavior
- Monitor everything via a real-time terminal dashboard

#### What You'll Learn

- Disaggregated prefill/decode architecture and why it improves efficiency
- KV-cache transfer between GPU pools
- Kubernetes orchestration for ML workloads
- Prometheus-based monitoring and autoscaling

#### Outcomes

- A running disaggregated inference cluster on Kubernetes
- Autoscaling policies that react to real inference metrics
- Load test data showing scaling behavior under pressure
- Experience with production-grade inference infrastructure

#### Quick Start

```bash
cd projects/advanced-infinite-scale
bash deploy.sh                    # Full stack deployment
python3 load_test.py              # Ramping load test
python3 dashboard.py              # Real-time monitoring
```

---

## Recommended Paths

Not sure where to start? Here are suggested paths:

**"I'm new to all of this"**
→ Start with **Ask My Docs** (beginner RAG). It produces a visible demo quickly and uses familiar concepts (web apps, APIs).

**"I want to understand how AI alignment works"**
→ Start with **Reward Ranker** (beginner RL), then graduate to **Align It** (intermediate DPO) if time allows.

**"I want to learn about model optimization"**
→ Start with **Shrink to Fit** (beginner quantization) to see the concept, then tackle **Compress & Compare** (intermediate) to do it yourself.

**"I'm experienced and want a challenge"**
→ Go straight to **Speed Demon** or **Align It**, or combine projects (e.g., quantize a model with Compress & Compare, then plug it into Ask My Docs).

**"I have K8s experience and want infrastructure"**
→ **Infinite Scale** (advanced) — but consider completing a beginner project first as a warm-up.
