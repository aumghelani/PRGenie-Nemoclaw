# Track 3 — Speculators Zoo (EAGLE / Medusa / N-gram / Draft-model)

Reference project for the Track 3 **Speculative Futures** Builder and Deep Tech lanes. The official page explicitly calls out:

> Train a speculator model for a specific use case. **Compare EAGLE, Medusa, and N-gram approaches**. Measure acceptance rates and throughput.
>
> **Automated speculation length tuning** that adapts to workload characteristics. Build a **regression test framework** to catch performance regressions across vLLM versions.

This project gives you runnable configurations for all four speculation strategies plus a harness that measures acceptance rate and end-to-end speedup for each.

## Why this project exists

The existing `projects/intermediate-speed-demon/` covers **draft-model** speculation only (using 8B to draft for 70B). That's one point in the design space. The Builder lane asks attendees to compare it against EAGLE, Medusa, and N-gram — so this project fills that gap.

## What's here

```
README.md                         # This file
install.sh                        # Install IBM Speculators v0.3.0 + EAGLE/Medusa weights
serve_configs/
  draft_model.sh                  # 8B drafts for 70B
  eagle.sh                        # EAGLE head on 70B
  medusa.sh                       # Medusa heads on 70B
  ngram.sh                        # N-gram speculation (no draft model)
  no_speculation.sh               # Baseline
measure_acceptance.py             # Measures accept-rate + tok/s for each config
auto_tune_spec_length.py          # Deep Tech: workload-adaptive k tuning
regression/
  spec_regression_test.py         # CI gate: fails if spec speedup drops >X%
  README.md                       # How to wire into GitHub Actions
```

## Quick start (Builder lane)

```bash
# 1. Install Speculators + fetch EAGLE/Medusa weights (~10 GB download)
bash install.sh

# 2. Run the comparison — spins up each config in turn, benchmarks, tears down
python3 measure_acceptance.py --all

# 3. Results land in results/acceptance_rates.csv
```

Expected output:

| Config        | Speedup | Acceptance rate | Note |
|---------------|---------|-----------------|------|
| baseline (no spec) | 1.00× | n/a         | Reference |
| N-gram        | ~1.15×  | ~40%            | Cheapest; no draft model needed |
| draft 8B→70B  | ~1.80×  | ~70%            | Classic vLLM spec |
| EAGLE-70B     | ~2.40×  | ~85%            | Head trained on target |
| Medusa-70B    | ~2.10×  | ~80%            | Multiple heads, more memory |

Actual numbers depend on GPU, workload, and version — that's the point of running the comparison.

## Deep Tech lane: adaptive speculation length

The `--num-speculative-tokens k` knob trades off per-step latency (higher `k` = more forward compute) against acceptance rate (higher `k` = more rejections). The optimal `k` depends on workload:

- **Long generation (code, summaries):** higher `k` (5-9) pays off
- **Short chat replies:** lower `k` (2-3) wins because late rejections waste less
- **Highly structured output:** very high acceptance → high `k`

`auto_tune_spec_length.py` implements a simple bandit that observes per-request acceptance and adjusts `k` live. Compare against a fixed-`k` baseline to show the gain.

## Regression test framework

`regression/spec_regression_test.py` runs a canonical workload, compares the measured speedup against a committed baseline JSON, and exits non-zero if the speedup has regressed. Copy the workflow template into `.github/workflows/` — it'll run on every PR that touches serving config.

## Speculators v0.3.0

[IBM Speculators](https://github.com/IBM/speculators) is the ecosystem for training and distributing speculator models. The event page explicitly calls out v0.3.0. Use it to:

- Fine-tune an EAGLE head on your domain's data (Builder lane bonus)
- Publish your speculator to HF for others to reuse (Open-Source Contribution points)

See `install.sh` for the install and a minimal training entry point (commented out by default — training takes hours).

## Suggested submission angles

- **"The only apples-to-apples speculator comparison on vLLM 2026.x"** — clean table + bar chart. Judges love this.
- **"Adaptive `k` beats fixed `k` by N% on mixed workloads"** — novel methodology; Innovation points.
- **"Spec-decode regression CI for vLLM"** — the `regression/` kit as a reusable GitHub Action. Direct candidate for **Best Upstream Contribution** prize.

## Links

- [IBM Speculators](https://github.com/IBM/speculators)
- [vLLM speculative decoding docs](https://docs.vllm.ai/en/latest/features/spec_decode.html)
- [EAGLE paper](https://arxiv.org/abs/2401.15077)
- [Medusa paper](https://arxiv.org/abs/2401.10774)
- [Leviathan et al. — original speculative decoding paper](https://arxiv.org/abs/2211.17192)
