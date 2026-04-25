# Speed Demon — Speculative Decoding Benchmark Showdown

**Level:** Intermediate | **Tier:** 2 (Performance) | **GPU:** 2x A100 (80 GB)

Measure how much speculative decoding accelerates Llama 3.1 70B inference by
using the 8B model as a draft. Sweep key parameters, compare workload profiles,
and generate visual dashboards of latency vs. throughput trade-offs.

---

## Quick Start

```bash
# 1. Run the full benchmark suite (baseline + speculative, all workloads)
bash run_benchmark_suite.sh

# 2. Or run individual benchmarks
bash benchmark_baseline.sh        # 70B without speculation
bash benchmark_speculative.sh     # 70B with 8B draft model

# 3. Sweep speculation depth and plot results
python3 sweep_spec_tokens.py
python3 plot_results.py
```

Results and charts are saved to the `results/` directory.

---

## How It Works

```
                  Speculative Decoding
                  ====================

  Draft Model (8B)          Target Model (70B)
  ================          ==================
  Generate K tokens  ---->  Verify all K in ONE forward pass
  (fast, cheap)             (expensive, but batched)

  If draft is correct:  accept all K tokens  (2-3x speedup)
  If draft is wrong:    reject at divergence, resample from target
```

The speedup depends on the **acceptance rate** — how often the draft model's
predictions match the target. Routine text (common phrases, code boilerplate)
has high acceptance; creative or specialized content has lower acceptance.

---

## Files

| File | Purpose |
|---|---|
| `run_benchmark_suite.sh` | Orchestrates the full benchmark pipeline |
| `benchmark_baseline.sh` | Starts 70B server (no speculation) and runs load test |
| `benchmark_speculative.sh` | Starts 70B with 8B draft and runs load test |
| `sweep_spec_tokens.py` | Varies `--num-speculative-tokens` (1-9) and collects metrics |
| `plot_results.py` | Generates comparison charts from benchmark data |
| `workloads.json` | Defines workload profiles (short chat, long-form, code) |

---

## What to Measure

| Metric | Why it matters |
|---|---|
| **Tokens/sec (throughput)** | How fast the system generates output |
| **Time-to-first-token (TTFT)** | Latency before generation starts |
| **End-to-end latency (P50/P99)** | Total request duration |
| **Acceptance rate** | Fraction of draft tokens accepted by target |
| **GPU utilization** | Are both GPUs saturated? |

---

## Ideas to Extend

- **Quantized draft model:** Use AWQ 4-bit 8B as draft — does smaller draft = faster?
- **Different workload mixes:** Code vs. prose vs. multi-turn chat
- **Concurrent users:** Sweep request concurrency (1, 4, 8, 16) under speculation
- **Draft model alternatives:** Try a different small model as draft
- **Accuracy check:** Run lm-eval on baseline vs. speculative to confirm quality parity

---

## Configuration

Default settings match the Tier 2 Brev instance. To customize:

```bash
# Use different ports (e.g., run baseline and speculative side-by-side)
VLLM_PORT=8001 bash benchmark_speculative.sh

# Change number of benchmark requests
NUM_REQUESTS=200 bash benchmark_baseline.sh
```
