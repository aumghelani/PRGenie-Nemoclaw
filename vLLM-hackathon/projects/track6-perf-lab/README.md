# Track 6 — Performance Tuning & Evaluation

Starter kit for the Performance Tuning & Evaluation track. Covers all three skill lanes:

| Lane | What you produce |
|------|------------------|
| **Starter** | GuideLLM run across 3 workload scenarios + visualized TTFT/TPS/throughput |
| **Builder** | Automated eval pipeline wired to Prometheus + Grafana; optimal params per scenario |
| **Deep Tech** | Profiled vLLM internals + CI-ready regression test framework |

## What's in this directory

```
scenarios/
  chat.yaml              # Short interactive prompts, low latency requirement
  code.yaml              # Long completions, reasoning heavy
  summarize.yaml         # Large inputs, small outputs
  run_all.sh             # Driver that benches all 3 and writes JSON

prometheus/
  prometheus.yml         # Scrape config for vLLM /metrics
  alert-rules.yml        # Example alerts (p99 latency, queue depth)

grafana/
  vllm-dashboard.json    # Starter dashboard: TTFT, TPS, queue, KV-cache hit rate

docker-compose.yaml      # Prometheus + Grafana stack (2 commands to run)

regression/
  baseline.json          # Commit baseline metrics to git
  check_regression.py    # CI script: fails build if p99 latency > baseline * 1.10
  .github-workflow.yml   # Copy into .github/workflows/ to wire up CI

profile_vllm.py          # py-spy + torch.profiler wrapper; finds hot functions
```

## Quick start (Starter lane)

```bash
# 1. vLLM already running on your Brev instance at :8000
curl -s http://localhost:8000/health

# 2. Run the three scenarios (takes ~15 min total)
bash scenarios/run_all.sh

# 3. Results land in results/*.json
python3 -c "import json; print(json.dumps(json.load(open('results/chat.json')), indent=2))"
```

GuideLLM writes TTFT, TPS, throughput, and queue-wait percentiles. Build a chart from the JSON (plotly, matplotlib — your choice).

## Builder lane: Prometheus + Grafana

```bash
# 1. Start the monitoring stack (works with docker or podman)
source ../../scripts/container-runtime.sh  # sets $COMPOSE_CMD for you
$COMPOSE_CMD up -d
# Equivalently:  docker compose up -d    OR    podman-compose up -d

# 2. Point your vLLM at :9091 (Prometheus scrapes /metrics automatically)
# vLLM exposes /metrics by default — nothing extra to configure

# 3. Open Grafana
open http://localhost:3000              # user: admin / pass: admin
# Dashboard → Import → upload grafana/vllm-dashboard.json
```

Tune the vLLM launch args (`--max-num-seqs`, `--max-num-batched-tokens`, `--enable-chunked-prefill`, etc.) and watch the impact in Grafana live. Document the optimal config per scenario.

## Deep Tech lane: profile + regression

```bash
# Profile a 2-minute workload to find hot functions
python3 profile_vllm.py --duration 120 --output profile.svg

# Commit the current perf as the regression baseline
python3 regression/check_regression.py --save regression/baseline.json

# Now every future run checks against baseline; fails if regressed > 10%
python3 regression/check_regression.py --baseline regression/baseline.json
```

The `.github-workflow.yml` template shows how to wire this into CI — a PR that regresses p99 latency by >10% auto-fails.

## Suggested Track 6 submission angles

- **"The vLLM perf dashboard everyone can use"** — polish the Grafana JSON + Prometheus recording rules and open a PR against the vLLM docs. Good for **Best Upstream Contribution** prize.
- **"Regression CI for vLLM"** — wrap `check_regression.py` as a reusable GitHub Action. High upstream-contribution potential.
- **"Which knob matters most?"** — run the Builder pipeline across a parameter sweep (`--max-num-seqs` × `--enable-chunked-prefill` × quantization) and produce a one-page cheat sheet.

## What this exercises

- GuideLLM workload scenarios and metrics schema
- Prometheus scrape config + recording rules for LLM metrics
- Grafana dashboard JSON schema
- py-spy + PyTorch profiler for finding Python/CUDA hot paths
- CI patterns for catching perf regressions

## Links

- [GuideLLM](https://github.com/neuralmagic/guidellm)
- [vLLM `/metrics` endpoint](https://docs.vllm.ai/en/latest/serving/metrics.html)
- [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)
