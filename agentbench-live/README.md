# AgentBench Live

**Red Hat Open Accelerator vLLM Hackathon — Boston, April 25, 2026**
**Track:** Deep Tech · NVIDIA GPU Prize
**Stack:** vLLM + NeMo Agent Toolkit + NemoClaw + Nemotron-Nano + React

A real-time agent performance profiler and auto-optimizer. Runs a 4-LLM-call
research agent, captures every LLM/tool span, visualizes the critical path
on a live Gantt chart, then auto-applies vLLM optimizations and shows the
before/after speedup.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       Browser dashboard                           │
│   React + Recharts · live Gantt · before/after metrics panel     │
└──────────────────────────────┬───────────────────────────────────┘
                               │ WebSocket /ws + REST /api
┌──────────────────────────────▼───────────────────────────────────┐
│              FastAPI server  (api_server/main.py)                 │
│   /tasks · /benchmark/run · /benchmark/{id} · /ws/{id}            │
└─────────────┬──────────────────────────┬──────────────────────────┘
              │                          │
   ┌──────────▼─────────┐    ┌───────────▼──────────────┐
   │  Subject Agent     │    │   Optimizer Agent         │
   │  4 LLM calls       │    │   critical-path / paral-  │
   │  4-8 tool calls    │    │   lelism / OSL analysis   │
   │  prefix-cache-     │    │   → vLLM flag diff +      │
   │  friendly prompts  │    │     human recs            │
   └──────────┬─────────┘    └──────────────────────────┘
              │  OpenAI-compatible HTTP
              │  + nvext priority/OSL headers
   ┌──────────▼───────────────────────────────────────┐
   │            vLLM   (Brev / WSL2 GPU host)         │
   │   --enable-prefix-caching   --kv-cache-dtype fp8 │
   │   --speculative-model       --tool-call-parser   │
   └──────────────────────────────────────────────────┘
```

## Repo layout

```
agentbench-live/
├── vllm_setup/          bash scripts you run ON the GPU host (Brev/WSL)
├── subject_agent/       the 4-call research agent under benchmark
├── benchmark_runner/    runs N×baseline + N×optimized, dumps JSON
├── optimizer_agent/     trace analyzer + recommender (the meta-agent)
├── nat_middleware/      nvext header builder + OSL trie predictor
├── api_server/          FastAPI + WebSocket bridge
├── dashboard/           Vite + React UI (npm install ready)
├── traces/              JSON trace output (gitignored)
├── scripts/             dev_up.ps1 · dev_up.sh · run_baseline · run_optimized
└── tests/               pytest unit tests for telemetry + optimizer
```

## Quick start (Windows / dev)

```powershell
# 1. Activate the venv (already created)
.venv\Scripts\Activate.ps1

# 2. Run unit tests — should pass without a vLLM endpoint
pytest -q

# 3. Start backend + dashboard side-by-side
.\scripts\dev_up.ps1

# Browser → http://localhost:5173
```

The dashboard will work without vLLM running, but `Run baseline` will fail
until you point `VLLM_BASE_URL` at a live vLLM endpoint.

## Hackathon-day workflow

1. **On the Brev/cloud GPU box:**
   ```bash
   bash vllm_setup/00_install.sh
   bash vllm_setup/01_smoke_test.sh
   bash vllm_setup/03_serve_nemotron.sh         # leave running in tmux
   ```
2. **On your laptop** (or wherever the dashboard runs):
   ```powershell
   $env:VLLM_BASE_URL = "http://<brev-ip>:5000/v1"
   .\scripts\dev_up.ps1
   ```
3. **For the demo:**
   - run task `econ-three-countries` in baseline mode
   - swap to `vllm_setup/04_serve_optimized.sh` (Ctrl+C the baseline server first)
   - run the same task in optimized mode
   - point at the Gantt charts shrinking and the metrics panel updating

## CLI usage

```bash
# Run one task in baseline mode
python scripts/run_baseline.py econ-three-countries --repeats 3

# Run the same task with optimizations + nvext headers
python scripts/run_optimized.py econ-three-countries --repeats 3

# Run both back-to-back and emit the headline comparison JSON
python scripts/run_compare.py econ-three-countries --repeats 3
```

Traces land in `traces/<task_id>__<mode>.json`.

## What each optimization does (and where it lives)

| Optimization | Where to flip it | Expected gain |
|---|---|---|
| Prefix caching | `vllm_setup/*.sh` add `--enable-prefix-caching` | 3-10× TTFT on calls 2-N |
| FP8 KV cache | `--kv-cache-dtype fp8` | 2× context length |
| Spec decoding | `--speculative-model PATH --num-speculative-tokens 5` | 1.5-1.7× decode |
| Async tool exec | `subject_agent/agent.py` already uses `asyncio.gather` | eliminates serial blocks |
| nvext priority headers | `nat_middleware/headers.py` + agent_config | -62% to -89% TTFT under load |
| Continuous batching | vLLM default — no flag | better GPU utilization |

## References

- vLLM: https://github.com/vllm-project/vllm
- NeMo Agent Toolkit: https://github.com/NVIDIA/NeMo-Agent-Toolkit
- NemoClaw: https://github.com/NVIDIA/NemoClaw
- Speculators: https://github.com/vllm-project/speculators
- The battle plan + Boston meetup deck: see `../docs/`
