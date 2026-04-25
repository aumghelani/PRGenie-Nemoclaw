# Hackathon Project Suggestions

Projects organized by topic, each with a beginner and intermediate option.
Every project includes complete, runnable code in the [`projects/`](projects/) directory.

Each project includes complete, runnable code in the [`projects/`](projects/) directory.

---

## RAG & Application Building

### Beginner: "Ask My Docs" — RAG-Powered Q&A App

**Track:** RAG on Open Inference / BYOP
**Tier:** Tier 1 — App Builder

#### What You'll Build

A Retrieval-Augmented Generation app that lets users upload documents (PDFs, markdown, text) and ask natural-language questions about them. The app ingests docs into ChromaDB, retrieves relevant chunks, and sends them as context to Llama 3.1 8B running on vLLM — all behind a Gradio UI.

#### Why This Project

- Uses the pre-built FastAPI scaffold and test client already on the Tier 1 image
- LangChain, ChromaDB, and Gradio are pre-installed — no dependency wrangling
- Only requires Python and basic REST API knowledge
- Produces a visible, demo-able product in a few hours

#### Recommended Configuration

| Setting | Value |
|---|---|
| **Brev Instance** | Tier 1 — App Builder |
| **GPU** | 1× L40S (48 GB) |
| **Model** | `/models/llama-3.1-8b-instruct` |
| **vLLM flags** | `--max-model-len 8192 --gpu-memory-utilization 0.85 --dtype auto` |
| **Embedding model** | `bge-small-en-v1.5` (pre-downloaded) |
| **Frontend** | Gradio (pre-installed) |

#### Getting Started

```bash
# 1. Start the vLLM server
bash /workspace/start_vllm_server.sh

# 2. Ingest the sample documents into ChromaDB
cd projects/beginner-ask-my-docs
python3 ingest.py

# 3. Launch the Gradio Q&A app
python3 app.py
# Open http://localhost:7860
```

#### Project Files

See [`projects/beginner-ask-my-docs/`](projects/beginner-ask-my-docs/) for the complete implementation:
- `app.py` — Gradio UI + RAG pipeline
- `ingest.py` — Document ingestion into ChromaDB
- `sample-docs/` — Example documents to test with

### Intermediate: "Speed Demon" — Speculative Decoding Benchmark Showdown

**Track:** Speculative Futures + Performance Tuning
**Tier:** Tier 2 — Performance

#### What You'll Build

A comparative benchmark suite that measures Llama 3.1 70B inference **with and without** speculative decoding (using the 8B model as draft). You'll tune draft token counts, measure acceptance rates, and produce a visual dashboard of latency vs. throughput trade-offs across different workload profiles (short chat, long-form generation, code completion).

#### Why This Project

- Requires understanding the draft/verify cycle of speculative decoding
- Involves meaningful parameter tuning and quantitative analysis
- Benchmarking scripts and profiling tools are pre-installed
- Produces charts and data you can present to judges
- Stretch goal: layer in AWQ/GPTQ quantization for further speedups

#### Recommended Configuration

| Setting | Value |
|---|---|
| **Brev Instance** | Tier 2 — Performance |
| **GPU** | 2× A100 (80 GB) |
| **Target model** | `/models/llama-3.1-70b-instruct` with `--tensor-parallel-size 2` |
| **Draft model** | `/models/llama-3.1-8b-instruct` |
| **vLLM flags** | `--tensor-parallel-size 2 --speculative-model /models/llama-3.1-8b-instruct --num-speculative-tokens 5` |
| **Benchmarking** | `guidellm`, `bench_throughput.sh` |
| **Profiling** | `nvtop`, `py-spy` |

#### Getting Started

```bash
cd projects/intermediate-speed-demon

# Option A: Run the full suite (baseline -> speculative -> charts)
bash run_benchmark_suite.sh

# Option B: Run individually
bash benchmark_baseline.sh          # 70B without speculation
bash benchmark_speculative.sh       # 70B with 8B draft (K=5)
python3 plot_results.py             # Generate comparison charts

# Option C: Sweep speculation depth (K=1,3,5,7,9)
python3 sweep_spec_tokens.py
python3 plot_results.py
```

#### Project Files

See [`projects/intermediate-speed-demon/`](projects/intermediate-speed-demon/) for the complete implementation:
- `run_benchmark_suite.sh` — Full pipeline orchestrator
- `benchmark_baseline.sh` / `benchmark_speculative.sh` — Individual benchmark scripts
- `sweep_spec_tokens.py` — Automated K-value sweep
- `plot_results.py` — Chart generation (throughput, latency, distributions)
- `workloads.json` — Workload profiles (short chat, long-form, code)

---

## Quantization (Model Compression)

Quantization reduces model precision (e.g., 16-bit to 4-bit) to shrink VRAM usage ~4x and boost throughput — the key technique for deploying LLMs cost-effectively and running them locally.

### Beginner: "Shrink to Fit" — Quantize and Serve a Compressed LLM

**Topic:** Quantization | **Tier:** Tier 1 — App Builder

#### What You'll Build

Download a pre-quantized 4-bit AWQ model, serve it alongside the full-precision original using vLLM, and compare them side-by-side in a Gradio app. See first-hand how a 16 GB model compressed to ~4 GB still produces great results.

#### Why This Project

- No quantization expertise needed — uses pre-quantized weights from HuggingFace
- Dramatic visual result: same quality, 4x less VRAM, faster inference
- Teaches the core concept through direct observation
- Gradio comparison app makes it easy to demo

#### Recommended Configuration

| Setting | Value |
|---|---|
| **Brev Instance** | Tier 1 — App Builder |
| **GPU** | 1× L40S (48 GB) |
| **Full model** | `/models/llama-3.1-8b-instruct` on port 8000 |
| **Quantized model** | `llama-3.1-8b-instruct-awq-int4` on port 8001 |
| **vLLM flags** | `--gpu-memory-utilization 0.45` per model (both share one GPU) |

#### Getting Started

```bash
cd projects/beginner-shrink-to-fit

# 1. Download the pre-quantized model (~4 GB, takes 1-2 min)
python3 download_quantized.py

# 2. Serve both models side-by-side
bash serve_both.sh

# 3. Launch the comparison UI
python3 compare_app.py
# Open http://localhost:7860
```

#### Project Files

See [`projects/beginner-shrink-to-fit/`](projects/beginner-shrink-to-fit/) for the complete implementation:
- `download_quantized.py` — Downloads pre-quantized AWQ model
- `serve_both.sh` — Runs full + quantized models on separate ports
- `compare_app.py` — Gradio side-by-side comparison with timing
- `benchmark_both.py` — Automated throughput and VRAM comparison

### Intermediate: "Compress & Compare" — Quantize Your Own Model

**Topic:** Quantization | **Tier:** Tier 2 — Performance

#### What You'll Build

Run the quantization process yourself using GPTQ and AWQ, then rigorously measure the quality vs. speed trade-off with academic benchmarks (lm-eval) and throughput tests. Produce a Pareto chart showing where each variant sits.

#### Why This Project

- Hands-on experience with the quantization calibration pipeline
- Compare two leading methods (GPTQ vs. AWQ) head-to-head
- Combines model optimization with rigorous evaluation methodology
- Produces quantitative results and charts for your presentation

#### Recommended Configuration

| Setting | Value |
|---|---|
| **Brev Instance** | Tier 2 — Performance |
| **GPU** | 2× A100 (80 GB) |
| **Base model** | `/models/llama-3.1-8b-instruct` |
| **GPTQ output** | `/models/llama-3.1-8b-instruct-gptq-4bit` |
| **AWQ output** | `/models/llama-3.1-8b-instruct-awq-4bit` |
| **Quality eval** | `lm-eval` (HellaSwag, ARC-Easy) |
| **Speed eval** | Custom throughput benchmark |

#### Getting Started

```bash
cd projects/intermediate-compress-and-compare

# 1. Quantize with GPTQ (~20 min)
python3 quantize_gptq.py

# 2. Quantize with AWQ (~15 min)
python3 quantize_awq.py

# 3. Evaluate quality (lm-eval benchmarks)
bash evaluate_quality.sh

# 4. Benchmark throughput for all variants
bash benchmark_all.sh

# 5. Generate trade-off charts
python3 plot_tradeoffs.py
```

#### Project Files

See [`projects/intermediate-compress-and-compare/`](projects/intermediate-compress-and-compare/) for the complete implementation:
- `quantize_gptq.py` — GPTQ 4-bit quantization with llm-compressor
- `quantize_awq.py` — AWQ 4-bit quantization with AutoAWQ
- `evaluate_quality.sh` — lm-eval quality benchmarks on all variants
- `benchmark_all.sh` — Throughput benchmark with VRAM tracking
- `plot_tradeoffs.py` — Pareto chart and comparison bar charts

---

## Reinforcement Learning (RLHF / DPO)

Reinforcement learning from human feedback (RLHF) is how modern LLMs are aligned to be helpful, harmless, and honest. These projects walk through the alignment pipeline from data collection to model fine-tuning.

### Beginner: "Reward Ranker" — Build a Human Feedback Loop

**Topic:** Reinforcement Learning | **Tier:** Tier 1 — App Builder

#### What You'll Build

A Gradio app where the LLM generates two responses to the same prompt (at different temperatures) and you pick the winner. Your preferences train a **reward model** — a classifier that learns to predict which responses humans prefer. This is Steps 1-3 of the RLHF pipeline.

#### Why This Project

- Fun and interactive — you're literally teaching an AI what "good" means
- Builds intuition for how alignment works at major AI labs
- Only requires Python knowledge; TRL handles the ML complexity
- The reward model you train is a real artifact you can demo

#### Recommended Configuration

| Setting | Value |
|---|---|
| **Brev Instance** | Tier 1 — App Builder |
| **GPU** | 1× L40S (48 GB) |
| **LLM** | `/models/llama-3.1-8b-instruct` via vLLM |
| **Reward model base** | `distilbert-base-uncased` (small, trains fast) |
| **Libraries** | TRL, transformers, datasets (pre-installed) |

#### Getting Started

```bash
# 1. Start vLLM
bash /workspace/start_vllm_server.sh

# 2. Collect preferences (rank at least 20-30 pairs)
cd projects/beginner-reward-ranker
python3 collect_preferences.py
# Open http://localhost:7860

# 3. Train a reward model on your preferences
python3 train_reward_model.py

# 4. See it score new responses
python3 score_responses.py
```

#### Project Files

See [`projects/beginner-reward-ranker/`](projects/beginner-reward-ranker/) for the complete implementation:
- `collect_preferences.py` — Gradio app for side-by-side ranking
- `train_reward_model.py` — Trains reward model with TRL's RewardTrainer
- `score_responses.py` — Scores new responses with the trained model
- `sample_prompts.json` — 20 curated prompts across categories

### Intermediate: "Align It" — Fine-tune with DPO

**Topic:** Reinforcement Learning | **Tier:** Tier 2 — Performance

#### What You'll Build

Actually **change the model's behavior** using Direct Preference Optimization (DPO). Generate preference data, run DPO training on Llama 3.1 8B with LoRA adapters (~100 MB, not 16 GB), serve the aligned model, and measure improvement in a before/after evaluation.

DPO is simpler and more stable than classic RLHF (no separate reward model or PPO needed) and is increasingly the industry standard for alignment.

#### Why This Project

- Covers the full alignment pipeline: data -> training -> serving -> evaluation
- LoRA makes it memory-efficient (fits on 2x A100 with room to spare)
- Produces a tangible before/after difference you can demo
- Directly relevant to enterprise LLM customization

#### Recommended Configuration

| Setting | Value |
|---|---|
| **Brev Instance** | Tier 2 — Performance |
| **GPU** | 2× A100 (80 GB) |
| **Base model** | `/models/llama-3.1-8b-instruct` |
| **LoRA rank** | 16 (adapter size ~50-100 MB) |
| **DPO beta** | 0.1 (alignment strength) |
| **Libraries** | TRL, PEFT, transformers, datasets (pre-installed) |

#### Getting Started

```bash
cd projects/intermediate-align-it

# 1. Start vLLM and generate preference data (~50 pairs)
python3 generate_preferences.py

# 2. Run DPO training with LoRA (~20-40 min)
python3 train_dpo.py

# 3. Serve base + aligned models side-by-side
bash serve_aligned.sh

# 4. Evaluate alignment improvement
python3 evaluate_alignment.py
```

#### Project Files

See [`projects/intermediate-align-it/`](projects/intermediate-align-it/) for the complete implementation:
- `generate_preferences.py` — Creates preference pairs from the base model
- `train_dpo.py` — DPO training with TRL + LoRA
- `serve_aligned.sh` — Serves base and aligned models on separate ports
- `evaluate_alignment.py` — Before/after comparison with win rate scoring

---

## Distributed Inference (Aspirational)

> **Note:** This project requires familiarity with Kubernetes and distributed systems.
> It is included as an **aspirational/optional** challenge for experienced attendees.
> Most teams should start with one of the projects above and attempt this only if
> they finish early or have prior K8s experience.

### Advanced: "Infinite Scale" — Disaggregated Prefill/Decode with llm-d on Kubernetes

**Track:** Inference at Scale
**Tier:** Tier 3 — Deep Tech

#### What You'll Build

A fully disaggregated inference deployment on Kubernetes where **prefill and decode phases run on separate GPU pools**, connected via KV-cache-aware routing. You'll deploy llm-d with Helm, configure autoscaling policies based on Prometheus metrics (queue depth, time-to-first-token, tokens-per-second), and demonstrate dynamic GPU allocation under varying load.

#### Recommended Configuration

| Setting | Value |
|---|---|
| **Brev Instance** | Tier 3 — Deep Tech |
| **GPU** | 4× A100 (80 GB) |
| **Model** | Llama 3.1 70B distributed across prefill + decode pools |
| **Orchestration** | kind cluster -> llm-d Helm chart |
| **Helm values** | `values-70b-distributed.yaml` (prefill/decode split) |
| **Monitoring** | Prometheus + k9s |

#### Getting Started

```bash
cd projects/advanced-infinite-scale

bash deploy.sh                   # Full stack deployment
python3 load_test.py             # Ramping load test
python3 dashboard.py             # Real-time monitoring dashboard
```

#### Project Files

See [`projects/advanced-infinite-scale/`](projects/advanced-infinite-scale/) for the complete implementation.

---

## Quick Reference

| Topic | Level | Project | Tier | GPU | Key Challenge |
|---|---|---|---|---|---|
| RAG / Apps | Beginner | Ask My Docs | 1 | 1× L40S | Build a RAG app with Gradio + ChromaDB |
| RAG / Apps | Intermediate | Speed Demon | 2 | 2× A100 | Benchmark speculative decoding trade-offs |
| Quantization | Beginner | Shrink to Fit | 1 | 1× L40S | Compare full vs. quantized model side-by-side |
| Quantization | Intermediate | Compress & Compare | 2 | 2× A100 | Quantize with GPTQ/AWQ, evaluate quality vs. speed |
| RL / Alignment | Beginner | Reward Ranker | 1 | 1× L40S | Collect preferences, train a reward model |
| RL / Alignment | Intermediate | Align It | 2 | 2× A100 | DPO fine-tuning with LoRA adapters |
| Distributed | Advanced | Infinite Scale | 3 | 4× A100 | Disaggregated prefill/decode on K8s *(aspirational)* |
