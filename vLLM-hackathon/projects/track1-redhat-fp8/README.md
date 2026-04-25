# Track 1 Deep Tech — Red Hat AI + FP8 + Compound Gains

Showcase project for the Track 1 **Lean Inference Challenge** Deep Tech lane. Demonstrates what the official event page asks for explicitly:

> Multi-strategy optimization: combine **FP8/MXFP4** quantization with speculative decoding. Build a benchmark harness that measures **compound gains**.

## What's here

```
README.md                          # This file
pull_redhat_models.py              # Download Red Hat AI's pre-quantized FP8 models
quantize_fp8_yourself.py           # Use LLM Compressor to produce FP8 yourself
quantize_mxfp4.py                  # MXFP4 via LLM Compressor (newer, vLLM 0.8+)
benchmark_compound.py              # Stack FP8 + speculative decoding, measure
serve_configs/
  fp16_baseline.sh                 #   Baseline: no optimization
  fp8_redhat.sh                    #   Red Hat pre-quantized FP8
  fp8_self_quantized.sh            #   Your own FP8 output
  fp8_plus_speculation.sh          #   FP8 target + FP16 8B draft
  mxfp4_plus_speculation.sh        #   MXFP4 + speculation (max compression)
results/                           # Auto-created when you run benchmarks
```

## Why Red Hat models

The event lists **Red Hat AI Models** as a Track 1 starter. The [RedHatAI HF org](https://huggingface.co/RedHatAI) hosts pre-quantized FP8 and INT4 variants of popular models that are known to run well on vLLM. Using these:

- Saves 20–30 min of quantization time at the hack
- Gives attendees a credible baseline to compare against
- Is aligned with event sponsor messaging

## Quick start (Starter lane)

```bash
# 1. Grab Red Hat's pre-quantized FP8 Llama 3.1 8B
python3 pull_redhat_models.py --model RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8

# 2. Serve it
bash serve_configs/fp8_redhat.sh &

# 3. Benchmark against the FP16 baseline
bash serve_configs/fp16_baseline.sh &   # in another terminal
python3 benchmark_compound.py --compare fp16 fp8-redhat
```

Expected: ~1.7–2.0× throughput, identical MMLU / HellaSwag scores (RedHatAI publishes the eval numbers on their model cards).

## Builder lane — quantize yourself

```bash
# ~20 min on an A100
python3 quantize_fp8_yourself.py \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --output /models/llama-3.1-8b-instruct-fp8-mine \
    --calibration-samples 256

# Compare your quant vs. Red Hat's — they should be close
python3 benchmark_compound.py --compare fp8-redhat fp8-mine
```

## Deep Tech lane — compound gains

This is the headline demo for the track. The idea: **quantization and speculative decoding are orthogonal speedups**. Stacking them should multiply, not add.

```bash
# Measure each lever in isolation and combined
python3 benchmark_compound.py --compound-matrix
```

The script runs 6 configurations:

| # | Quant | Speculation | Expected speedup vs. FP16 baseline |
|---|-------|-------------|------------------------------------|
| 1 | FP16 | none       | 1.0× (baseline) |
| 2 | FP8  | none       | ~1.8× |
| 3 | FP16 | draft-8B   | ~1.5× |
| 4 | FP8  | draft-8B   | ~2.6× (compound) |
| 5 | MXFP4| none       | ~2.2× |
| 6 | MXFP4| draft-8B   | ~3.1× (compound, aggressive) |

It outputs a CSV + Pareto chart. Hand this to the judges — it's one-pager gold.

## MXFP4 notes

MXFP4 is a newer shared-scale 4-bit format that preserves accuracy better than INT4 for many models. Requires **vLLM ≥ 0.8** and a recent LLM Compressor build. Not all model architectures are supported yet — check the [LLM Compressor FP8 guide](https://github.com/vllm-project/llm-compressor/blob/main/examples/quantization_w4a16_fp8_mixed/README.md).

## Suggested submission angle

Frame the project as "**a reusable compound-gains harness for vLLM**":

- The `benchmark_compound.py` matrix is genuinely useful beyond the event
- Pair it with a GitHub Action that runs the matrix on each PR
- That's a direct candidate for the **Best Upstream Contribution** prize

## Links

- [Red Hat AI on Hugging Face](https://huggingface.co/RedHatAI)
- [LLM Compressor FP8 guide](https://github.com/vllm-project/llm-compressor/tree/main/examples/quantization_w8a8_fp8)
- [LLM Compressor MXFP4 guide](https://github.com/vllm-project/llm-compressor/tree/main/examples/quantization_w4a16_fp8_mixed)
- [vLLM FP8 docs](https://docs.vllm.ai/en/latest/quantization/fp8.html)
