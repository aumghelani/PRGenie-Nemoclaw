# CLAUDE.md

Guidelines for AI assistants working in this repository.

## Repository Overview

This is a hackathon kit for the **TOA vLLM/LLM-D Hackathon** (April 25, 2026,
Boston). It contains 7 starter projects across 4 topics (RAG, quantization,
reinforcement learning, distributed inference), environment setup scripts for
3 GPU tiers, a ZeroClaw demo, and attendee documentation.

**This is NOT a typical software project.** It is a collection of independent
starter projects, setup scripts, and documentation. There is no shared library,
no build system, no test suite, and no CI/CD pipeline.

## Directory Structure

```
vLLM-hackathon/
├── CLAUDE.md                  # This file
├── README.md                  # Repo overview
├── attendee-guide.md          # Attendee-facing environment guide
├── hackathon-project-suggestions.md  # Detailed project descriptions
├── hackathon-gpu-cost-estimate.xlsx  # GPU cost estimates
├── LICENSE                    # MIT
├── demo/                      # ZeroClaw code assistant demo
│   ├── install.sh             # One-command setup
│   ├── config.ollama.toml     # Local (Ollama) config
│   ├── config.vllm.toml       # GPU (vLLM) config
│   ├── skills/                # 5 skill definitions (local + cloud)
│   └── examples/              # Sample code and walkthrough
├── launchable-configs/        # Brev environment setup (3 tiers)
│   ├── tier1-app-builder/     # 1x L40S, 48 GB
│   ├── tier2-performance/     # 2x A100, 80 GB each
│   └── tier3-deep-tech/       # 4x A100, 80 GB each
└── projects/                  # 7 starter projects
    ├── README.md              # Project overview and decision guide
    ├── USE_CASES.md           # Real-world use cases per project
    ├── beginner-ask-my-docs/          # RAG Q&A app
    ├── beginner-shrink-to-fit/        # Quantization comparison
    ├── beginner-reward-ranker/        # RLHF preference collection
    ├── intermediate-speed-demon/      # Speculative decoding benchmarks
    ├── intermediate-compress-and-compare/  # DIY quantization + evaluation
    ├── intermediate-align-it/         # DPO fine-tuning with LoRA
    └── advanced-infinite-scale/       # Disaggregated K8s inference
```

## Key Conventions

### Project Organization
- Projects are named `<level>-<slug>` (e.g., `beginner-ask-my-docs`)
- Each project is self-contained with its own README, scripts, and code
- No shared dependencies between projects; each stands alone

### Common Assumptions Across All Projects
- **vLLM** serves models via OpenAI-compatible API at `http://localhost:8000/v1`
- **Model paths** follow `/models/llama-3.1-8b-instruct` (8B) and `/models/llama-3.1-70b-instruct` (70B)
- **Python 3.11+**, CUDA, and PyTorch are pre-installed on Brev instances
- The startup script `/workspace/start_vllm_server.sh` is created by the tier setup scripts

### GPU Tier Mapping
| Tier | GPU | Projects |
|------|-----|----------|
| 1 (App Builder) | 1x L40S, 48 GB | ask-my-docs, shrink-to-fit, reward-ranker |
| 2 (Performance) | 2x A100, 80 GB | speed-demon, compress-and-compare, align-it |
| 3 (Deep Tech) | 4x A100, 80 GB | infinite-scale |

### Technology Stack by Topic
- **RAG & Apps:** LangChain, ChromaDB, sentence-transformers, Gradio, FastAPI
- **Quantization:** AWQ, GPTQ, llm-compressor, AutoAWQ, lm-eval
- **Reinforcement Learning:** TRL (RewardTrainer, DPOTrainer), PEFT/LoRA
- **Distributed Inference:** Kubernetes (kind), llm-d, Helm, Prometheus

## Git Conventions

- **Branch naming:** `claude/<description>-<ID>` for feature branches
- **Commit messages:** Start with action verb ("Add", "Update", "Fix"), describe changes clearly
- **Default branch:** `main`

## Working with This Repo

### When Adding or Editing Projects
- Each project must have a standalone `README.md` with: quick start, architecture, file listing, and extension ideas
- Scripts should be idempotent and include error handling for missing dependencies
- Use `#!/usr/bin/env bash` and `set -euo pipefail` in shell scripts
- Python scripts should include clear docstrings at the top explaining purpose and usage

### When Editing Documentation
- The primary attendee-facing docs are `attendee-guide.md` and `projects/README.md`
- Keep `projects/README.md` in sync when adding/removing projects
- Use the existing table format in `projects/README.md` for consistency
- Keep quick-start instructions to 3-4 commands max

### When Editing Setup Scripts (`launchable-configs/`)
- Setup scripts run once during Brev instance provisioning
- They install system packages, Python libraries, and pre-download models
- Each tier script creates `/workspace/start_vllm_server.sh` and `/workspace/test_setup.sh`
- Changes to setup scripts affect all attendees; test thoroughly

### File Types in This Repo
- `.md` — Documentation (most of the repo)
- `.py` — Starter Python code for projects
- `.sh` — Bash scripts (setup, benchmarking, serving)
- `.json` — Sample data (prompts, workload profiles)
- `.yaml` — Kubernetes configs (autoscale policies, Prometheus rules)
- `.toml` — ZeroClaw configuration
- `.xlsx` — Cost estimates (binary, do not edit programmatically)

## Do NOT

- Add CI/CD pipelines — this is a hackathon kit, not a production project
- Add root-level requirements.txt or pyproject.toml — dependencies are managed per-tier in setup scripts
- Modify `.xlsx` files programmatically
- Create test suites for the starter projects — they are intentionally minimal scaffolds
- Add complexity to starter code — simplicity is a feature for hackathon participants
