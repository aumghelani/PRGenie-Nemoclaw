# TOA vLLM / LLM-D Hackathon — Attendee Environment Guide

**Date:** April 25, 2026 | **Location:** The Open Accelerator, Fortpoint, Boston

---

## Getting Started (< 2 minutes)

Every team gets a pre-configured GPU cloud instance on NVIDIA Brev — no local setup required. Your mentor will share a Launchable link for your track. Click it, sign in to Brev, and you'll have a running environment with models pre-loaded and tools installed.

Once your instance is up:

```bash
# 1. Validate everything is working
bash /workspace/test_setup.sh

# 2. Start the LLM server
bash /workspace/start_vllm_server.sh    # (Tier 1)
bash /workspace/serving/serve_8b_baseline.sh  # (Tier 2/3)

# 3. Test it
python3 /workspace/test_client.py
```

Your vLLM server exposes an **OpenAI-compatible API** at `http://localhost:8000/v1` — use it with any OpenAI client library, LangChain, or plain HTTP requests.

> 📝 **Pre-event prep note:** the event page lists **Podman** in the prerequisite tools. Brev instances ship with **Docker** — functionally equivalent for our purposes. Podman works everywhere in this repo **except Track 5** (NemoClaw specifically requires Docker). Full compatibility matrix in [`docs/PODMAN-NOTES.md`](docs/PODMAN-NOTES.md). Sourceable shim: `scripts/container-runtime.sh`.

> 🏆 **Prize reminder:** the event has a dedicated **Best Upstream Contribution** prize worth real points. See [`docs/UPSTREAM-CONTRIBUTION-GUIDE.md`](docs/UPSTREAM-CONTRIBUTION-GUIDE.md) for a repo-by-repo target list, per-track PR angles, and a submission checklist. Every starter kit in [`projects/`](projects/) also flags specific upstream PR opportunities in its "Submission angles" section.

---

## Choose Your Environment

| | **Tier 1: App Builder** | **Tier 2: Performance** | **Tier 3: Deep Tech** | **Tier 4: Agentic Edge** 🏆 |
|---|---|---|---|---|
| **GPU** | 1× L40S (48GB) | 2× A100 80GB | 4× A100 80GB | 1× A100/H100 80GB |
| **Models** | Llama 3.1 8B | 8B + 70B | 8B + 70B | Llama 3.1 8B (+ Nemotron profiles) |
| **Best for** | RAG, apps, products | Quantization, speculative decoding, benchmarking | Distributed inference, llm-d, K8s | Autonomous agents, tool-calling, steering |
| **Tracks** | 2 (RAG), 5a (BYOP), 6 (Eval) | 1 (Lean Inference), 3 (Spec Decode), 6 (Eval) | 4 (Inference at Scale), 1 & 3 (Deep Tech lane) | **5 (Agentic Edge — NVIDIA GPU Prize)** |
| **Skill lane** | Starter / Builder | Builder / Deep Tech | Deep Tech | Starter / Builder / Deep Tech |

**Not sure which to pick?** If you want to build an app or demo, go Tier 1. If you want to make models faster, go Tier 2. If you want to run a distributed inference cluster, go Tier 3. **If you want to build autonomous agents for the NVIDIA GPU Prize, go Tier 4.**

---

## What's Pre-Installed

### All Tiers
- Python 3.11+, CUDA, PyTorch
- vLLM (latest) — LLM serving engine
- Llama 3.1 8B Instruct — pre-downloaded, ready to serve
- guidellm, lm-eval — evaluation and load testing
- llm-compressor — model quantization
- Jupyter Lab (accessible via Brev one-click)

### Tier 1 Additionally
- LangChain + ChromaDB + BGE embedding model (for RAG)
- FastAPI app scaffold at `/workspace/app-scaffold/`
- Gradio (for quick UI prototyping)

### Tier 2 Additionally
- Llama 3.1 70B Instruct — pre-downloaded
- AutoGPTQ, AutoAWQ — quantization backends
- Benchmarking scripts at `/workspace/benchmarks/`
- Speculative decoding config at `/workspace/benchmarks/speculative_decoding.sh`
- nvtop, py-spy — GPU and profiling tools

### Tier 3 Additionally
- Everything in Tier 2, plus:
- kubectl, Helm, kind, k9s — full Kubernetes stack
- llm-d repo with Helm charts at `/workspace/llm-d/`
- Pre-built llm-d deployment configs at `/workspace/llm-d-configs/`
- Disaggregated prefill/decode configuration for 70B
- Inference monitoring dashboard

### Tier 4 Additionally (Agentic Edge / NVIDIA GPU Prize)
- NemoClaw + OpenShell sandbox runtime
- vLLM launched with `--enable-auto-tool-choice` for structured tool calls
- Four inference profiles wired in `blueprint.yaml` (vLLM, vLLM+steered, NIM-local, NVIDIA-cloud)
- Agent scaffolds at `/workspace/nemoclaw-agent/` (Starter, Builder, Deep Tech)
- Latency benchmark harness for profile comparison
- Docker + Node 20 (required by NemoClaw)

---

## Quick Recipes by Track

### Track 1: Lean Inference Challenge (Quantization)
```bash
# --- Starter: pre-quantized Red Hat AI model (fastest path) ---
cd projects/track1-redhat-fp8
python3 pull_redhat_models.py --model 8b-fp8
bash serve_configs/fp8_redhat.sh

# --- Builder: quantize it yourself ---
python3 /workspace/benchmarks/quantize_model.py              # GPTQ
python3 projects/track1-redhat-fp8/quantize_fp8_yourself.py  # FP8 via LLM Compressor

# --- Deep Tech: compound gains (FP8 + MXFP4 + spec decoding) ---
python3 projects/track1-redhat-fp8/benchmark_compound.py --compound-matrix
```
Full kit: [projects/track1-redhat-fp8/README.md](projects/track1-redhat-fp8/README.md)

### Track 2: RAG on Open Inference
```python
# --- Starter: LangChain + vLLM (beginner kit) ---
# See: projects/beginner-ask-my-docs/
from langchain_community.llms import VLLMOpenAI
llm = VLLMOpenAI(
    openai_api_base="http://localhost:8000/v1",
    model_name="/models/llama-3.1-8b-instruct",
    openai_api_key="not-needed"
)
```
```bash
# --- Builder: LlamaIndex + BGE reranker + RAGAs evaluation ---
cd projects/track2-ragas-rerank
pip install llama-index llama-index-vector-stores-chroma \
    llama-index-embeddings-huggingface \
    llama-index-postprocessor-flag-embedding-reranker ragas
python3 ingest.py --docs sample-docs/
python3 query_with_reranker.py "How does vLLM handle KV-cache?"
python3 eval_with_ragas.py   # produces faithfulness / relevancy / precision scores
```
Full kit: [projects/track2-ragas-rerank/README.md](projects/track2-ragas-rerank/README.md)

### Track 3: Speculative Futures
```bash
# --- Starter: classic draft-model speculation ---
bash /workspace/benchmarks/speculative_decoding.sh

# --- Builder: compare EAGLE / Medusa / N-gram / draft-model side-by-side ---
cd projects/track3-speculators-zoo
bash install.sh                             # Speculators v0.3.0 + EAGLE/Medusa weights
python3 measure_acceptance.py --all         # full comparison → results/acceptance_rates.csv

# --- Deep Tech: adaptive k and regression CI ---
python3 auto_tune_spec_length.py            # bandit over k ∈ {2,3,5,7}
python3 regression/spec_regression_test.py --save regression/baseline.json
```
Full kit: [projects/track3-speculators-zoo/README.md](projects/track3-speculators-zoo/README.md)

### Track 4: Inference at Scale
```bash
# --- Starter: deploy vLLM behind the llm-d Inference Gateway ---
bash /workspace/scripts/start_kind_cluster.sh
bash /workspace/scripts/deploy_llm_d.sh /workspace/llm-d-configs/values-8b.yaml

# --- Builder: multi-model + A/B canary + per-pool HPA ---
cd projects/track4-inference-gateway
bash scripts/deploy_gateway.sh helm-values/values-multi-model.yaml
python3 scripts/send_mixed_traffic.py --multi-model       # observe routing
bash scripts/deploy_gateway.sh helm-values/values-ab-split.yaml
bash scripts/shift_traffic.sh 50 50                        # canary ramp without redeploy

# --- Deep Tech: disaggregated 70B + autoscaling (existing) ---
bash /workspace/scripts/deploy_llm_d.sh /workspace/llm-d-configs/values-70b-distributed.yaml
```
Full kits: [projects/track4-inference-gateway/README.md](projects/track4-inference-gateway/README.md) · [projects/advanced-infinite-scale/README.md](projects/advanced-infinite-scale/README.md)

### Track 5: Agentic Edge powered by NemoClaw 🏆 (NVIDIA GPU Prize)
Build high-accuracy, steerable agents on top of vLLM using NemoClaw's sandboxed runtime. Three tiers:

- **Starter** — vibe-code an agent UI with Cursor on the starter template
- **Builder** — extend the multi-turn customer support reference agent with your own tools
- **Deep Tech** — implement custom steering and benchmark latency across inference profiles

```bash
# (Tier 4 Launchable — see launchable-configs/tier4-nemoclaw/)
# 1. Start vLLM with tool-calling enabled
bash /workspace/start_vllm_server.sh

# 2. Onboard NemoClaw against the local vLLM endpoint
bash /workspace/onboard_nemoclaw.sh

# 3. Connect to the sandbox and run the reference agent
nemoclaw agentic-edge connect
python3 /workspace/nemoclaw-agent/customer_support_agent.py

# Deep Tech: compare inference profiles
python3 /workspace/nemoclaw-agent/benchmarks/latency-test.py --profile vllm
python3 /workspace/nemoclaw-agent/benchmarks/latency-test.py --profile vllm-steered
```
Full track guide: [demo/nemoclaw-agent/README.md](demo/nemoclaw-agent/README.md)

### Track 5a (formerly Track 5): BYOP — Build Your Own Product
```bash
# Start the LLM backend
bash /workspace/start_vllm_server.sh

# Start the app scaffold
cd /workspace/app-scaffold && bash run.sh

# Your app is at http://localhost:8080
# Edit main.py to build your product!
```

### Track 6: Performance Tuning & Evaluation
```bash
# --- Starter: run the 3-scenario GuideLLM sweep ---
cd projects/track6-perf-lab
bash scenarios/run_all.sh                   # chat + code + summarize workloads → results/*.json

# --- Builder: wire Prometheus + Grafana live dashboards ---
docker compose up -d                        # or: podman-compose up -d
# Open Grafana at http://localhost:3000 (admin/admin), import grafana/vllm-dashboard.json

# --- Deep Tech: profile + regression CI ---
python3 profile_vllm.py --duration 120 --output profile.svg
python3 regression/check_regression.py --save regression/baseline.json

# --- Alternative starters (existing tools still work) ---
lm_eval --model vllm --model_args pretrained=/models/llama-3.1-8b-instruct \
    --tasks hellaswag,arc_easy --batch_size auto
guidellm --target http://localhost:8000/v1 --model /models/llama-3.1-8b-instruct
```
Full kit: [projects/track6-perf-lab/README.md](projects/track6-perf-lab/README.md)

---

## Accessing Your Environment

- **Jupyter:** Click "Open Jupyter" in the Brev console — no extra setup
- **SSH:** Use the Brev CLI (`brev shell <instance-name>`) or the SSH command shown in the Brev console
- **API endpoint:** Exposed via Cloudflare tunnel — the URL appears in the Brev console under Networking
- **AI coding tools:** Cursor, Copilot, and Claude are all encouraged — connect them via SSH remote to your Brev instance

---

## Bonus: Run an LLM on Your Laptop with ZeroClaw

Want to see what quantization can do? The **ZeroClaw Code Assistant demo** runs a quantized Llama 3.1 8B (~4.5 GB) directly on your laptop — no GPU, no cloud, no cost for most tasks. Complex requests (architecture review, security audit) automatically route to a cloud model.

```bash
# From the repo's demo/ directory
bash install.sh
export ANTHROPIC_API_KEY="sk-ant-..."   # only needed for cloud-routed tasks
zeroclaw start
```

**On your Brev GPU instance**, you can use vLLM as the backend instead of Ollama for faster inference:

```bash
cp demo/config.vllm.toml ~/.zeroclaw/config.toml
cp demo/skills/*.md ~/.zeroclaw/workspace/skills/
zeroclaw start
```

See the full [demo walkthrough](demo/examples/walkthrough.md) for a guided script with sample code to try.

---

## Starter Projects

Not sure what to build? We have complete, runnable starter projects organized by topic. Each includes all scripts, configs, and sample data you need.

### Track-specific kits (built for each official challenge)

| Track | Kit | Directory | What You'll Build |
|---|---|---|---|
| **1** Deep Tech | Red Hat AI + FP8 | [`projects/track1-redhat-fp8/`](projects/track1-redhat-fp8/) | Red Hat pre-quantized models + FP8/MXFP4 + compound-gains harness |
| **2** Builder | RAGAs + Reranker | [`projects/track2-ragas-rerank/`](projects/track2-ragas-rerank/) | LlamaIndex + BGE cross-encoder reranker + RAGAs evaluation |
| **3** Builder / Deep Tech | Speculators Zoo | [`projects/track3-speculators-zoo/`](projects/track3-speculators-zoo/) | EAGLE / Medusa / N-gram / draft-model comparison + regression CI |
| **4** Builder | Inference Gateway | [`projects/track4-inference-gateway/`](projects/track4-inference-gateway/) | Multi-model + A/B canary + per-pool autoscaling |
| **4** Deep Tech | Infinite Scale | [`projects/advanced-infinite-scale/`](projects/advanced-infinite-scale/) | Disaggregated 70B on K8s with HPA + Prometheus |
| **5** 🏆 | NemoClaw agent | [`demo/nemoclaw-agent/`](demo/nemoclaw-agent/) | Starter scaffold, multi-turn reference agent, 4-profile benchmark |
| **6** all lanes | Perf Lab | [`projects/track6-perf-lab/`](projects/track6-perf-lab/) | GuideLLM scenarios + Prometheus/Grafana + profiling + regression gate |

### RAG & Application Building

| Level | Project | Directory | What You'll Build |
|---|---|---|---|
| **Beginner** | Ask My Docs | [`projects/beginner-ask-my-docs/`](projects/beginner-ask-my-docs/) | RAG Q&A app with Gradio + ChromaDB |
| **Intermediate** | Speed Demon | [`projects/intermediate-speed-demon/`](projects/intermediate-speed-demon/) | Speculative decoding benchmark suite with charts |

### Quantization (Model Compression)

| Level | Project | Directory | What You'll Build |
|---|---|---|---|
| **Beginner** | Shrink to Fit | [`projects/beginner-shrink-to-fit/`](projects/beginner-shrink-to-fit/) | Compare full vs. 4-bit quantized model side-by-side |
| **Intermediate** | Compress & Compare | [`projects/intermediate-compress-and-compare/`](projects/intermediate-compress-and-compare/) | Quantize with GPTQ/AWQ, benchmark quality vs. speed |

### Reinforcement Learning (RLHF / DPO)

| Level | Project | Directory | What You'll Build |
|---|---|---|---|
| **Beginner** | Reward Ranker | [`projects/beginner-reward-ranker/`](projects/beginner-reward-ranker/) | Collect human preferences, train a reward model |
| **Intermediate** | Align It | [`projects/intermediate-align-it/`](projects/intermediate-align-it/) | DPO fine-tuning with LoRA adapters |

### Distributed Inference *(Aspirational)*

| Level | Project | Directory | What You'll Build |
|---|---|---|---|
| **Advanced** | Infinite Scale | [`projects/advanced-infinite-scale/`](projects/advanced-infinite-scale/) | Disaggregated inference on K8s with autoscaling |

See [`hackathon-project-suggestions.md`](hackathon-project-suggestions.md) for full details, recommended configurations, and extension ideas.

---

## Troubleshooting

**vLLM server won't start / OOM error:**
Reduce `--max-model-len` (try 4096 or 2048) or lower `--gpu-memory-utilization` to 0.80.

**Model download seems stuck:**
Models are pre-cached. If they're missing, run: `huggingface-cli download meta-llama/Llama-3.1-8B-Instruct --local-dir /models/llama-3.1-8b-instruct`

**Can't access the API externally:**
Check the Cloudflare tunnel URL in the Brev console. If using port-forwarding: `ssh -L 8000:localhost:8000 <your-brev-ssh-command>`

**GPU not detected:**
Run `nvidia-smi`. If it fails, your instance may still be provisioning — wait 1-2 minutes and retry.

**Need help?** Raise your hand — core vLLM and llm-d committers are here as mentors.

---

## Useful Links

- [vLLM Documentation](https://docs.vllm.ai/)
- [vLLM GitHub](https://github.com/vllm-project/vllm)
- [llm-d Documentation](https://llm-d.ai/docs/)
- [llm-d GitHub](https://github.com/llm-d/llm-d)
- [NVIDIA Brev Console](https://brev.nvidia.com/)
- [Brev Launchables Docs](https://docs.nvidia.com/brev/concepts/launchables)
- [Llama 3.1 Model Card](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)
- [ZeroClaw](https://github.com/zeroclaw-labs/zeroclaw)
- [Ollama](https://ollama.com/)
- [NemoClaw (NVIDIA)](https://github.com/NVIDIA/NemoClaw)
- [NemoClaw (brevdev)](https://github.com/brevdev/NemoClaw)
- [NemoClaw local inference guide](https://docs.nvidia.com/nemoclaw/latest/inference/use-local-inference.html)
- [Brev console reference](https://docs.nvidia.com/brev/latest/guides/console-reference)
- [One-click Launchables blog](https://developer.nvidia.com/blog/one-click-deployments-for-the-best-of-nvidia-ai-with-nvidia-launchables/)

### In-repo references
- [`docs/TRACK-ALIGNMENT-REVIEW.md`](docs/TRACK-ALIGNMENT-REVIEW.md) — what each track-kit covers and the current gap-closure status
- [`docs/UPSTREAM-CONTRIBUTION-GUIDE.md`](docs/UPSTREAM-CONTRIBUTION-GUIDE.md) — per-track PR angles (for the Best Upstream Contribution prize)
- [`docs/PODMAN-NOTES.md`](docs/PODMAN-NOTES.md) — Docker vs. Podman compatibility matrix
