# Shrink to Fit — Quantize and Serve a Compressed LLM

**Level:** Beginner | **Topic:** Quantization (Model Compression) | **Tier:** 1 (App Builder) | **GPU:** 1x L40S (48 GB)

See first-hand how a 16 GB model can be compressed to ~4 GB and still produce
great results. You'll download a pre-quantized model, serve it with vLLM,
and compare it side-by-side against the full-precision original using a
Gradio interface.

---

## Quick Start

```bash
# 1. Download the pre-quantized 4-bit AWQ model
python3 download_quantized.py

# 2. Start the vLLM server with BOTH models (full + quantized)
bash serve_both.sh

# 3. Launch the side-by-side comparison UI
python3 compare_app.py
# Open http://localhost:7860
```

---

## What is Quantization?

Quantization reduces the precision of a model's weights — for example, from
16-bit floating point (2 bytes per weight) down to 4-bit integers (0.5 bytes
per weight). This makes the model **~4x smaller** in memory, which means:

- **Fits on smaller GPUs** — or fits alongside other workloads
- **Faster inference** — less data to move through memory bandwidth
- **Runs locally** — small enough for laptops (via Ollama, llama.cpp)

The trade-off is a small quality loss. This project lets you see that trade-off
yourself.

```
Full Precision (FP16)          Quantized (INT4-AWQ)
==================             ====================
~16 GB VRAM                    ~4 GB VRAM
Baseline quality               ~98-99% of baseline quality
1x speed                       1.5-2x speed (memory-bound tasks)
```

---

## How It Works

```
                +------- Port 8000 ------+
                |  vLLM: Full 8B (FP16)  |
 User prompt -->|                        |--> Side-by-side in Gradio
                |  vLLM: 8B-AWQ (INT4)   |
                +------- Port 8001 ------+
```

The comparison app sends the same prompt to both models simultaneously and
displays the results side-by-side with timing information, so you can judge
quality and speed at a glance.

---

## Files

| File | Purpose |
|---|---|
| `download_quantized.py` | Downloads a pre-quantized AWQ model from HuggingFace |
| `serve_both.sh` | Starts two vLLM instances (full + quantized) on different ports |
| `compare_app.py` | Gradio app for side-by-side comparison |
| `benchmark_both.py` | Automated throughput and quality comparison |

---

## Ideas to Extend

- **Try different quantization levels:** Compare 4-bit vs. 8-bit AWQ
- **Memory profiling:** Use `nvidia-smi` to show VRAM savings visually
- **Longer prompts:** Does quality degrade more on complex reasoning tasks?
- **Batch throughput:** How much faster is quantized under concurrent load?
- **Chain it with RAG:** Swap the quantized model into the Ask My Docs project

---

## Why This Matters for Enterprise

Quantization is how companies deploy LLMs cost-effectively:
- **Edge deployment:** Run models on customer devices, no cloud needed
- **Cost reduction:** Serve 4x more users per GPU
- **Latency:** Faster responses for real-time applications
- **Privacy:** Keep data on-device by running models locally
