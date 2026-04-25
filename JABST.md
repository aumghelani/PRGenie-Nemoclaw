# JABST — AgentBench Live
### Red Hat / NVIDIA vLLM Hackathon · Deep Tech Track · April 25, 2026

> **For Claude:** When a friend opens this repo and starts a Claude session, read this file completely, then guide them through every install step below based on their machine. Ask them upfront: (1) Are you on Windows or Linux/Mac? (2) Do you have a GPU available? (3) Have you been given the HuggingFace token? Then run the correct installs for their setup.

---

## What This Project Is

**AgentBench Live** is a real-time AI agent performance profiler and auto-optimizer.

It runs a multi-step AI agent (4 LLM calls + 8 tool calls per task), records every millisecond of its work, then automatically finds the slowest parts and tells you exactly how to fix them — live, in a browser dashboard.

Think of it like a doctor running an EKG on an AI agent while it works, then prescribing the cure.

**The demo:** Run the same task twice — once with AI inference unoptimized, once with all optimizations on. The dashboard shows a before/after Gantt chart and a speedup table. Target: 3-10x faster.

---

## The Full Stack (What Lives in This Repo)

```
AgentBench Live
│
├── agentbench-live/              ← THE MAIN PROJECT
│   ├── api_server/               FastAPI backend + WebSocket streamer
│   ├── subject_agent/            The AI agent being profiled (4 LLM calls)
│   ├── benchmark_runner/         Runs baseline vs optimized comparisons
│   ├── optimizer_agent/          Analyzes traces, generates fix recommendations
│   ├── nat_middleware/           Adds priority headers to LLM requests
│   ├── dashboard/                React + Vite live dashboard (Gantt chart)
│   ├── scripts/                  dev_up.sh, run_compare.py
│   ├── vllm_setup/               Bash scripts for the GPU machine
│   └── tests/                    pytest unit tests
│
├── vLLM-hackathon/               ← HACKATHON KIT (reference + extras)
│   ├── projects/                 13 starter projects across 3 skill levels
│   ├── demo/nemoclaw-agent/      NemoClaw agentic edge starter template
│   └── launchable-configs/       Brev GPU environment setup configs
│
└── docs/                         ← READING MATERIAL
    ├── EXPLAIN_LIKE_IM_5.md      Plain-English explanation of the whole stack
    ├── Hackathon_Battle_Plan_...  Full architecture + hour-by-hour plan
    └── Boston vLLM Meetup...     Technical deck with benchmark numbers
```

---

## The Technology Stack Explained

### Layer 1 — Nemotron (The Brain)
NVIDIA's AI model: **Nemotron-Nano 30B**. Has 30 billion parameters but only activates 3 billion at a time (Mamba-Transformer hybrid). Best-in-class at multi-step tool calling. Runs on one A100/H100 GPU.

Downloaded from HuggingFace: `nvidia/NVIDIA-Nemotron-Nano-3-30B-A3B-BF16`

### Layer 2 — vLLM (The Engine)
Runs Nemotron on the GPU. Ships 5 optimizations we measure in this project:
- **Prefix Caching** — Don't re-read the same system prompt every call (3-10x TTFT reduction)
- **Speculative Decoding** — Guess 5 tokens ahead, verify all at once (1.5-1.7x speedup)
- **FP8 KV Cache** — Half-precision memory, doubles effective context length
- **Async Scheduling (MRV2)** — Overlap CPU prep with GPU compute (56% throughput gain)
- **Agentic Headers** — Tell vLLM which request is first/last in a chain so it priorities smartly

### Layer 3 — NemoClaw (The Sandbox)
NVIDIA's agent runtime. Wraps the agent in a secure environment: network isolation, file access control, YAML security policies. Also routes requests — local Nemotron vs cloud endpoints — based on data sensitivity.

### Layer 4 — NeMo Agent Toolkit / NAT (The Spy)
Middleware that sits between your agent code and the LLM. Records every call duration, token count, and time-to-first-token. Also adds `x-nvext-*` priority headers so vLLM knows which requests in a chain are most urgent. Our dashboard gets all its live data from NAT.

---

## Two-Machine Setup

This project runs across **two machines**:

| Machine | Role | What runs there |
|---|---|---|
| **Your laptop (Windows/Mac)** | Dev + Dashboard | FastAPI backend, React dashboard, Python agent code |
| **GPU server (Linux)** | Inference | vLLM serving Nemotron, NemoClaw, NAT |

The GPU server can be: a Brev Launchable, a WSL instance with a GPU, or any Linux box with an NVIDIA A100/H100/RTX 4090.

---

## Install Guide

> **For Claude:** Work through these sections with the user. Check what they have installed before running commands. Use `python --version`, `node --version`, `nvidia-smi` to verify. If something is already installed and at the right version, skip it.

---

### Part A — Laptop Setup (Everyone Does This)

#### A1. Python 3.12+
```bash
python --version   # must be 3.12 or higher
```
If not: download from python.org and install. Make sure to check "Add to PATH".

#### A2. Node.js 20+ and npm
```bash
node --version     # must be 20 or higher
npm --version
```
If not: download from nodejs.org (LTS version).

#### A3. Clone the repo and enter it
```bash
git clone <repo-url>
cd "Redhat Hackathon"
```

#### A4. Python virtual environment + dependencies
```bash
cd agentbench-live
python -m venv .venv

# Windows:
.venv\Scripts\activate

# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

This installs: FastAPI, Uvicorn, OpenAI SDK, WebSockets, Pydantic, pytest, numpy, and all other backend deps.

#### A5. Dashboard dependencies
```bash
cd dashboard
npm install
cd ..
```

#### A6. Environment file
```bash
cp .env.example .env
```
Then open `.env` and set:
```
VLLM_BASE_URL=http://<gpu-server-ip>:5000/v1
VLLM_MODEL=nemotron
HF_TOKEN=<token from Aum>
PORT=8000
```
If running GPU server locally (WSL): use `http://localhost:5000/v1`

#### A7. Verify the Python install works
```bash
# from agentbench-live/ with .venv active
python -c "import openai, fastapi, uvicorn; print('OK')"
```

---

### Part B — GPU Server Setup (Whoever Has the GPU Does This)

> This runs on Linux. If using WSL, open a WSL terminal. If using Brev, SSH into the instance.

#### B1. Verify GPU is available
```bash
nvidia-smi
# Must show a GPU. A100/H100/RTX 4090 recommended. Minimum 16GB VRAM for 8B fallback, 40GB+ for Nemotron 30B.
```

#### B2. Run the vLLM install script
```bash
cd vllm_setup
chmod +x 00_install.sh
./00_install.sh
```
This script:
- Creates a Python 3.12 virtual environment at `~/vllm-env`
- Installs vLLM + FlashInfer (fast attention kernels)
- Installs `huggingface_hub` CLI
- Prompts you to log in with your HuggingFace token

When it asks for token, paste the HF token Aum gave you.

#### B3. Smoke test vLLM
```bash
chmod +x 01_smoke_test.sh
./01_smoke_test.sh
```
Downloads a tiny model and verifies vLLM responds. Should print `{"id":"..."}` at the end.

#### B4. Install NemoClaw
```bash
curl -fsSL https://raw.githubusercontent.com/NVIDIA/NemoClaw/main/install.sh | bash
nemoclaw my-agent onboard
```

#### B5. Install NeMo Agent Toolkit
```bash
git clone https://github.com/NVIDIA/NeMo-Agent-Toolkit.git
cd NeMo-Agent-Toolkit
pip install -e .
cd ..
```

#### B6. Download and serve Nemotron (Baseline — no optimizations)
```bash
chmod +x 99_baseline_only.sh
./99_baseline_only.sh
```
This downloads `nvidia/NVIDIA-Nemotron-Nano-3-30B-A3B-BF16` (~60GB) on first run — takes 10-20 min depending on bandwidth. Then serves it on port 5000 with prefix caching OFF (baseline).

#### B7. Verify it works
```bash
curl http://localhost:5000/v1/models
# Should return {"object":"list","data":[{"id":"nemotron",...}]}
```

---

### Part C — Run the Demo

> Back on your laptop with `.venv` active.

#### Terminal 1 — Start the backend
```bash
cd agentbench-live
source .venv/bin/activate    # or .venv\Scripts\activate on Windows
uvicorn api_server.main:app --reload --port 8000
```

#### Terminal 2 — Start the dashboard
```bash
cd agentbench-live/dashboard
npm run dev
# Opens at http://localhost:5173
```

#### Terminal 3 — Quick CLI comparison (no UI needed for MVP)
```bash
cd agentbench-live
source .venv/bin/activate
python scripts/run_compare.py
```
This runs the same task baseline then optimized and prints the speedup table directly to terminal. **This alone is the MVP.**

---

### Part D — Run Optimized Mode

On the GPU server, stop the baseline server (Ctrl+C) and run:
```bash
./04_serve_optimized.sh
```
This enables: `--enable-prefix-caching`, `--kv-cache-dtype fp8`, speculative decoding (if a draft model is set).

Then re-run `python scripts/run_compare.py` — the second run should be noticeably faster.

---

## Fallback: No 30B GPU? Use Qwen3-8B Instead

If you only have a 24GB GPU (RTX 4090 or single A100 40GB):
```bash
./02_serve_qwen8b.sh
```
Then in your `.env` set `VLLM_MODEL=agent-model`. Everything else works the same.

---

## What Each Script Does

| Script | Where | What it does |
|---|---|---|
| `vllm_setup/00_install.sh` | GPU server | Installs vLLM + dependencies |
| `vllm_setup/01_smoke_test.sh` | GPU server | Verifies vLLM works |
| `vllm_setup/99_baseline_only.sh` | GPU server | Serves Nemotron, NO optimizations |
| `vllm_setup/04_serve_optimized.sh` | GPU server | Serves Nemotron, ALL optimizations ON |
| `scripts/run_baseline.py` | Laptop | One baseline run, saves trace JSON |
| `scripts/run_optimized.py` | Laptop | One optimized run, saves trace JSON |
| `scripts/run_compare.py` | Laptop | Both runs back-to-back, prints speedup table |
| `scripts/dev_up.sh` | Laptop | Starts backend + dashboard together |

---

## Troubleshooting

**"Connection refused" on port 5000**
The vLLM server isn't running. SSH to the GPU machine and check `./99_baseline_only.sh` is running in a tmux/screen session.

**"ModuleNotFoundError"**
Your `.venv` isn't active. Run `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Mac/Linux) first.

**Dashboard shows nothing / WebSocket error**
Make sure the FastAPI backend is running on port 8000. Check that `VLLM_BASE_URL` in `.env` points to the correct GPU server IP.

**Model download hangs or fails**
Your HuggingFace token isn't set or isn't authorized for Nemotron. Run `huggingface-cli login` on the GPU server and paste the token.

**Out of GPU memory**
Switch to the Qwen3-8B fallback (`02_serve_qwen8b.sh`). Alternatively, reduce `--max-model-len` in the serve script.

---

## Quick Architecture Diagram

```
Browser (localhost:5173)
    ↕ HTTP + WebSocket
FastAPI backend (localhost:8000)
    ├── /benchmark/run     → starts SubjectAgent
    ├── /ws/{run_id}       → streams span events live
    └── /benchmark/{id}    → returns full trace + recommendations
         ↓
    SubjectAgent
    ├── NAT Middleware     → adds x-nvext-* priority headers
    ├── LLM Call 1: Plan   → decomposes the question
    ├── Tool Calls (parallel): web_search, database_query
    ├── LLM Call 2: Synthesize
    ├── LLM Call 3: Gap Check + more tools
    └── LLM Call 4: Final Answer
         ↓
    OptimizerAgent
    └── Reads trace → outputs recommendations + vLLM flags
         ↓
GPU Server (port 5000)
    vLLM serving Nemotron-Nano-30B
    ├── Prefix Cache (shared system prompt across 4 calls)
    ├── FP8 KV Cache
    ├── Speculative Decoding (EAGLE-3)
    └── Async Scheduling (MRV2)
```

---

## Read More

- `docs/EXPLAIN_LIKE_IM_5.md` — Plain-English explanation of every piece (NemoClaw, Nemotron, vLLM, NAT)
- `agentbench-live/README.md` — Technical quick-start
- `docs/Hackathon_Battle_Plan_NemoClaw_Deep_Tech.pdf` — Full system design + hour-by-hour plan
- `vLLM-hackathon/projects/` — 13 other starter projects if you want to explore different tracks
