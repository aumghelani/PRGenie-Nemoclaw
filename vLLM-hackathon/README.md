# TOA vLLM / LLM-D Hackathon

**Date:** April 25, 2026 | **Location:** The Open Accelerator, Fortpoint, Boston

Materials for running a one-day hackathon focused on LLM inference with [vLLM](https://github.com/vllm-project/vllm) and [llm-d](https://github.com/llm-d/llm-d). Includes pre-configured GPU environments on NVIDIA Brev, setup scripts, benchmarking tools, and an attendee guide.

## What's in this repo

```
attendee-guide.md                        # Attendee-facing environment guide
hackathon-gpu-cost-estimate.xlsx         # GPU instance cost estimates by tier
launchable-configs/
  tier1-app-builder/                     # 1x L40S — RAG, apps, BYOP
    setup.sh                             #   Brev setup script (vLLM, LangChain, ChromaDB, Gradio)
    BREV_CONFIG.md                       #   Brev console configuration steps
  tier2-performance/                     # 2x A100 80GB — quantization, spec decode, benchmarking
    setup.sh                             #   Brev setup script (8B + 70B models, profiling tools)
    BREV_CONFIG.md                       #   Brev console configuration steps
  tier3-deep-tech/                       # 4x A100 80GB — distributed inference, llm-d, K8s
    setup.sh                             #   Brev setup script (full llm-d stack, kind, k9s)
    BREV_CONFIG.md                       #   Brev console configuration steps
  tier4-nemoclaw/                        # 1x A100/H100 — Agentic Edge (NVIDIA GPU Prize)
    setup.sh                             #   Brev setup script (NemoClaw + vLLM + agent scaffold)
    BREV_CONFIG.md                       #   Brev console configuration steps
docs/
  TRACK-ALIGNMENT-REVIEW.md              # Source-of-truth: track-by-track alignment + gap status
  UPSTREAM-CONTRIBUTION-GUIDE.md         # Target repos, per-track PR angles, submission checklist
  PODMAN-NOTES.md                        # Docker vs Podman compatibility matrix
  REVIEW-AND-IMPROVEMENTS.md             # Historical: initial Track 5 rationale + Brev deployment notes
scripts/
  container-runtime.sh                   # Shim: detects docker vs podman, exports $COMPOSE_CMD
projects/                                # Per-track starter projects
  track1-redhat-fp8/                     # Track 1 Deep Tech: Red Hat AI + FP8 + MXFP4 + compound gains
  track2-ragas-rerank/                   # Track 2 Builder: LlamaIndex + BGE rerank + RAGAs eval
  track3-speculators-zoo/                # Track 3: EAGLE/Medusa/N-gram/draft comparison + regression CI
  track4-inference-gateway/              # Track 4 Builder: multi-model + A/B canary + per-pool HPA
  track6-perf-lab/                       # Track 6: GuideLLM scenarios + Prometheus/Grafana + profiling
  # --- Level-tiered starters (match any track) ---
  beginner-ask-my-docs/                  # RAG + Gradio (Track 2)
  beginner-shrink-to-fit/                # Pre-quantized vs FP16 side-by-side (Track 1)
  beginner-reward-ranker/                # RLHF preference collection + reward model
  intermediate-speed-demon/              # 70B + speculative decoding sweep (Track 3)
  intermediate-compress-and-compare/     # GPTQ vs AWQ quality/speed Pareto (Track 1)
  intermediate-align-it/                 # DPO with LoRA adapters
  advanced-infinite-scale/               # llm-d disaggregated + HPA + Prometheus (Track 4)
demo/                                    # Hands-on demos
  # --- ZeroClaw code assistant (laptop + GPU) ---
  config.ollama.toml                     #   ZeroClaw config for laptop (Ollama backend)
  config.vllm.toml                       #   ZeroClaw config for GPU instance (vLLM backend)
  install.sh                             #   One-command setup for laptop
  skills/                                #   ZeroClaw skill definitions
    code-explain.md                      #     Explain code (local)
    code-refactor.md                     #     Refactor code (local)
    code-review.md                       #     Quick code review (local)
    architecture-review.md               #     Deep architecture review (cloud)
    security-audit.md                    #     Security audit (cloud)
  examples/
    sample_code.py                       #   Sample Python file with intentional issues
    walkthrough.md                       #   Step-by-step demo script
  # --- NemoClaw agentic edge (Track 5) ---
  nemoclaw-agent/
    README.md                            #   Track 5 guide (Starter / Builder / Deep Tech)
    setup.sh                             #   NemoClaw install + vLLM onboarding
    blueprint.yaml                       #   Inference profiles, tools, network policy
    starter-template.py                  #   Starter tier: minimal scaffold to vibe-code on
    customer_support_agent.py            #   Builder tier: multi-turn reference agent
    tools/                               #   KB search, orders, tickets, escalation
    benchmarks/
      latency-test.py                    #   Deep Tech: profile-comparison harness
```

## Tiers at a glance

| Tier | GPU | Models | Tracks |
|------|-----|--------|--------|
| **1 — App Builder** | 1x L40S (48 GB) | Llama 3.1 8B | RAG, BYOP, Eval |
| **2 — Performance** | 2x A100 80 GB | 8B + 70B | Quantization, Speculative Decode, Eval |
| **3 — Deep Tech** | 4x A100 80 GB | 8B + 70B | Distributed Inference, llm-d, K8s |
| **4 — Agentic Edge** 🏆 | 1x A100/H100 80 GB | Llama 3.1 8B + Nemotron profiles | **Track 5 — NVIDIA GPU Prize** |

## How to use

### 1. Create Brev Launchables

For each tier you plan to offer:

1. Open the [NVIDIA Brev Console](https://brev.nvidia.com/).
2. Follow the step-by-step instructions in the tier's `BREV_CONFIG.md`.
3. Paste the contents of the tier's `setup.sh` as the setup script.
4. Publish the Launchable with link sharing enabled.

Each Launchable will provision a GPU instance with models pre-downloaded, tools installed, and starter scripts ready to go.

### 2. Share with attendees

Distribute the Launchable links to attendees along with the [Attendee Guide](attendee-guide.md). The guide covers:

- How to connect to their environment (Jupyter, SSH, API)
- What's pre-installed per tier
- Quick-start recipes for each of the 6 hackathon tracks
- Troubleshooting common issues

### 3. Build a NemoClaw agent (Track 5 — NVIDIA GPU Prize)

The [`demo/nemoclaw-agent/`](demo/nemoclaw-agent/) directory contains the full Track 5 scaffold — Starter template, Builder reference agent, four inference profiles, and a latency benchmark harness. Deploy the Tier-4 Launchable and walk through the three tiers in `demo/nemoclaw-agent/README.md`.

```bash
bash /workspace/start_vllm_server.sh      # start vLLM with tool-calling enabled
bash /workspace/onboard_nemoclaw.sh       # wire NemoClaw to the local vLLM
nemoclaw agentic-edge connect             # enter the sandboxed agent environment
```

### 4. Run the ZeroClaw code assistant demo

The [`demo/`](demo/) directory contains a ready-to-run code assistant that shows how quantized local LLMs handle everyday coding tasks (explain, refactor, review) while automatically routing complex reasoning (architecture review, security audit) to a cloud model like Claude.

**On a laptop (Ollama):**
```bash
cd demo && bash install.sh
export ANTHROPIC_API_KEY="sk-ant-..."
zeroclaw start
```

**On a Brev GPU instance (vLLM):**
```bash
cp demo/config.vllm.toml ~/.zeroclaw/config.toml
cp demo/skills/*.md ~/.zeroclaw/workspace/skills/
zeroclaw start
```

See the full [demo walkthrough](demo/examples/walkthrough.md) for a guided script attendees can follow.

### 5. Estimate costs

Open `hackathon-gpu-cost-estimate.xlsx` to review and adjust GPU instance costs based on expected team count and session duration.

### 6. Review & plan

- [`docs/TRACK-ALIGNMENT-REVIEW.md`](docs/TRACK-ALIGNMENT-REVIEW.md) — source of truth for how each track-kit maps to the official event page, with the current gap-closure status.
- [`docs/UPSTREAM-CONTRIBUTION-GUIDE.md`](docs/UPSTREAM-CONTRIBUTION-GUIDE.md) — per-track paths to a merged PR (relevant for the Best Upstream Contribution prize).
- [`docs/PODMAN-NOTES.md`](docs/PODMAN-NOTES.md) — Podman vs. Docker compatibility matrix.
- [`docs/REVIEW-AND-IMPROVEMENTS.md`](docs/REVIEW-AND-IMPROVEMENTS.md) — historical Track 5 rationale and Brev/Launchable deployment notes.

## Hackathon tracks

Each track has three skill lanes (Starter / Builder / Deep Tech). Starter kits linked below:

1. **Lean Inference Challenge** — Quantize models and optimize throughput · [Track 1 Deep Tech kit](projects/track1-redhat-fp8/README.md) · [beginner quant starter](projects/beginner-shrink-to-fit/README.md) · [intermediate GPTQ/AWQ](projects/intermediate-compress-and-compare/README.md)
2. **RAG on Open Inference** — Build retrieval-augmented generation apps on vLLM · [Track 2 Builder kit (LlamaIndex + RAGAs + reranker)](projects/track2-ragas-rerank/README.md) · [beginner RAG starter](projects/beginner-ask-my-docs/README.md)
3. **Speculative Futures** — Speed up inference with speculative decoding · [Track 3 Speculators Zoo (EAGLE/Medusa/N-gram)](projects/track3-speculators-zoo/README.md) · [intermediate speed demon](projects/intermediate-speed-demon/README.md)
4. **Inference at Scale** — Deploy llm-d on Kubernetes with disaggregated serving · [Track 4 Builder kit (multi-model + A/B canary)](projects/track4-inference-gateway/README.md) · [advanced infinite scale (Deep Tech)](projects/advanced-infinite-scale/README.md)
5. **Agentic Edge powered by NemoClaw** 🏆 (NVIDIA GPU Prize) — High-accuracy, steerable agents on vLLM · [Track 5 guide](demo/nemoclaw-agent/README.md)
6. **Performance Tuning & Evaluation** — Benchmark and evaluate with GuideLLM / Prometheus / lm-eval · [Track 6 perf lab](projects/track6-perf-lab/README.md)

> 💡 **Best Upstream Contribution prize** is awarded to the work most likely to land as a merged PR in vLLM, llm-d, or related projects. Every track kit above flags specific submission angles that target upstream contribution directly.

## Links

- [vLLM Documentation](https://docs.vllm.ai/)
- [llm-d Documentation](https://llm-d.ai/docs/)
- [ZeroClaw](https://github.com/zeroclaw-labs/zeroclaw)
- [Ollama](https://ollama.com/)
- [NemoClaw (NVIDIA)](https://github.com/NVIDIA/NemoClaw) / [brevdev fork](https://github.com/brevdev/NemoClaw)
- [NemoClaw local inference guide](https://docs.nvidia.com/nemoclaw/latest/inference/use-local-inference.html)
- [NVIDIA Brev Console](https://brev.nvidia.com/)
- [Brev Launchables Docs](https://docs.nvidia.com/brev/concepts/launchables)
- [One-click Launchables blog](https://developer.nvidia.com/blog/one-click-deployments-for-the-best-of-nvidia-ai-with-nvidia-launchables/)
