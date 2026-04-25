# Notes for future Claude sessions

## What this is
Hackathon project for the **Red Hat Open Accelerator vLLM Hackathon** — Boston, April 25 2026, Deep Tech track / NVIDIA GPU Prize.

## Source of truth
- Battle plan: `../docs/Hackathon_Battle_Plan_NemoClaw_Deep_Tech.pdf`
- Boston meetup deck (March 31): `../docs/Boston vLLM Meetup - March 31, 2026.pdf`
- Pre-hack checklist: `../docs/pre-hack-vllm-infographic.png`

## Conventions
- All Python code lives at the repo root as flat top-level packages (`subject_agent`, `benchmark_runner`, `optimizer_agent`, `nat_middleware`, `api_server`). Imports between them use bare names — works because `pythonpath = ["."]` is set in `pyproject.toml`.
- Tests are in `tests/` and run with `pytest -q`. They do NOT need a vLLM endpoint.
- Telemetry uses a span model identical in shape to OpenTelemetry but stripped down so we can ship JSON traces directly to the dashboard.
- Prompts in `subject_agent/prompts.py` are deliberately structured for max prefix-cache hit rate: tool definitions in the system message, static-first / dynamic-last.

## Where each optimization is wired
| What | Where |
|---|---|
| `--enable-prefix-caching` | `vllm_setup/02..04_serve_*.sh` |
| `--kv-cache-dtype fp8` | `vllm_setup/04_serve_optimized.sh` |
| `--speculative-model …` | `vllm_setup/04_serve_optimized.sh` (set `DRAFT_MODEL` env var) |
| Async parallel tools | `subject_agent/agent.py` already uses `asyncio.gather` |
| nvext priority headers | `nat_middleware/headers.py` + `AgentConfig.nvext_*` fields |

## Demo flow
1. `vllm_setup/99_baseline_only.sh` (baseline server, no optimizations)
2. Dashboard `Run baseline` button — produces a Gantt chart
3. Ctrl+C the baseline server; start `vllm_setup/04_serve_optimized.sh`
4. Dashboard `Run optimized` button — Gantt chart visibly shorter
5. MetricsPanel shows the speedup table; RecommendationsPanel shows what the Optimizer Agent would have suggested

## What's intentionally NOT done
- No model weights are downloaded (too big, wrong machine)
- No actual NemoClaw or NeMo Agent Toolkit Python install — those run on the GPU host. Our `nat_middleware/` is a *compatible* lightweight implementation.
- No real `web_search` — `subject_agent/tools.py` mocks tool latencies deterministically. The whole point is to measure inference, not tools.
