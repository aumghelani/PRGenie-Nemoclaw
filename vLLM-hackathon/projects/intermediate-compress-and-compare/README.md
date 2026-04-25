# Compress & Compare — Quantize Your Own Model and Benchmark the Trade-offs

**Level:** Intermediate | **Topic:** Quantization (Model Compression) | **Tier:** 2 (Performance) | **GPU:** 2x A100 (80 GB)

Go beyond using pre-quantized models. Run the quantization process yourself
with different methods (GPTQ, AWQ) and bit widths (4-bit, 8-bit), then
rigorously measure the quality vs. speed trade-off using academic benchmarks
and throughput tests. Produce a trade-off chart that shows exactly where each
configuration sits on the Pareto frontier.

---

## Quick Start

```bash
# 1. Quantize the 8B model with GPTQ 4-bit
python3 quantize_gptq.py

# 2. Quantize with AWQ 4-bit
python3 quantize_awq.py

# 3. Run quality evaluation on all variants (lm-eval)
bash evaluate_quality.sh

# 4. Run throughput benchmarks on all variants
bash benchmark_all.sh

# 5. Generate the trade-off chart
python3 plot_tradeoffs.py
```

---

## What You'll Learn

| Concept | What it means |
|---|---|
| **Calibration** | Quantization uses a small dataset to decide how to best compress each layer |
| **GPTQ** | Post-training quantization using second-order information (Hessian) — high quality |
| **AWQ** | Activation-aware quantization — protects salient weights, fast to apply |
| **Perplexity** | Measures how "surprised" the model is — lower is better, tracks quality loss |
| **Pareto frontier** | The set of configurations where you can't improve speed without losing quality |

---

## Files

| File | Purpose |
|---|---|
| `quantize_gptq.py` | Quantize Llama 8B to GPTQ 4-bit using llm-compressor |
| `quantize_awq.py` | Quantize Llama 8B to AWQ 4-bit using AutoAWQ |
| `evaluate_quality.sh` | Run lm-eval benchmarks (HellaSwag, ARC) on each variant |
| `benchmark_all.sh` | Throughput benchmark for all variants |
| `plot_tradeoffs.py` | Generate quality-vs-speed Pareto chart |

---

## Quantization Variants Produced

| Variant | Method | Bits | Expected VRAM | Expected Quality |
|---|---|---|---|---|
| Original (FP16) | None | 16 | ~16 GB | Baseline (100%) |
| GPTQ 4-bit | GPTQ | 4 | ~4 GB | ~98-99% |
| AWQ 4-bit | AWQ | 4 | ~4 GB | ~98-99% |

---

## Ideas to Extend

- **8-bit variants:** Quantize at W8A8 for a gentler trade-off
- **Quantize the 70B model:** Compress it to fit on fewer GPUs
- **Mixed precision:** Quantize attention layers differently from FFN layers
- **Custom calibration data:** Use domain-specific text for calibration
- **Deploy to Ollama:** Export a GGUF and run it on your laptop

---

## Why This Matters for Enterprise

Every production LLM deployment involves quantization decisions:
- **Serving cost:** 4-bit models serve 4x more users per GPU-hour
- **Model selection:** A quantized 70B can outperform a full-precision 8B
- **SLA compliance:** Quantized models meet latency targets that FP16 cannot
- **Edge/on-prem:** Compressed models fit hardware constraints in regulated environments
