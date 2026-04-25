"""
Shrink to Fit — Automated benchmark comparing full vs quantized models.

Runs a set of prompts through both models and reports throughput, latency,
and VRAM usage. No Gradio needed — pure terminal output + JSON results.

Prerequisites:
    bash serve_both.sh   (models on ports 8000 and 8001)

Usage:
    python3 benchmark_both.py
    python3 benchmark_both.py --num-requests 30
"""

import argparse
import json
import os
import statistics
import subprocess
import time

import httpx

PROMPTS = [
    "Explain quantum computing in simple terms.",
    "Write a Python function to merge two sorted lists.",
    "What are the benefits of microservices architecture?",
    "Describe how DNS resolution works step by step.",
    "Write a SQL query to find the second highest salary in a table.",
    "Explain the difference between TCP and UDP.",
    "What is the CAP theorem?",
    "Write a Python decorator that logs function execution time.",
]

MODELS = [
    {
        "name": "Full Precision (FP16)",
        "url": "http://localhost:8000/v1/chat/completions",
        "model": "/models/llama-3.1-8b-instruct",
        "port": 8000,
    },
    {
        "name": "Quantized (AWQ INT4)",
        "url": "http://localhost:8001/v1/chat/completions",
        "model": "/models/llama-3.1-8b-instruct-awq-int4",
        "port": 8001,
    },
]


def get_gpu_memory() -> dict:
    """Get current GPU memory usage."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        gpus = {}
        for line in result.stdout.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 3:
                gpus[f"gpu_{parts[0]}"] = {
                    "used_mb": int(parts[1]),
                    "total_mb": int(parts[2]),
                }
        return gpus
    except Exception:
        return {}


def benchmark_model(model_config: dict, num_requests: int) -> dict:
    """Run benchmark against a single model."""
    url = model_config["url"]
    model = model_config["model"]
    latencies = []
    tokens_list = []

    for i in range(num_requests):
        prompt = PROMPTS[i % len(PROMPTS)]
        start = time.perf_counter()
        try:
            r = httpx.post(url, json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 128,
                "temperature": 0.1,
            }, timeout=120)
            elapsed = time.perf_counter() - start
            r.raise_for_status()
            tokens = r.json()["usage"]["completion_tokens"]
            latencies.append(elapsed)
            tokens_list.append(tokens)
        except Exception as e:
            print(f"    Request {i+1} failed: {e}")
            continue

        if (i + 1) % 10 == 0:
            print(f"    [{i+1}/{num_requests}] completed")

    total_tokens = sum(tokens_list)
    total_time = sum(latencies)

    return {
        "name": model_config["name"],
        "requests": len(latencies),
        "total_tokens": total_tokens,
        "total_time_s": total_time,
        "throughput_tps": total_tokens / total_time if total_time > 0 else 0,
        "latency_mean_ms": statistics.mean(latencies) * 1000 if latencies else 0,
        "latency_median_ms": statistics.median(latencies) * 1000 if latencies else 0,
        "latency_p95_ms": sorted(latencies)[int(0.95 * len(latencies))] * 1000 if latencies else 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-requests", type=int, default=20)
    args = parser.parse_args()

    print("=" * 55)
    print("  Shrink to Fit — Full vs Quantized Benchmark")
    print(f"  Requests per model: {args.num_requests}")
    print("=" * 55)

    # Capture VRAM before
    gpu_mem = get_gpu_memory()
    if gpu_mem:
        for gpu_id, mem in gpu_mem.items():
            print(f"  {gpu_id}: {mem['used_mb']} / {mem['total_mb']} MB used")
    print()

    results = []
    for model_config in MODELS:
        print(f"Benchmarking: {model_config['name']}")
        result = benchmark_model(model_config, args.num_requests)
        result["gpu_memory"] = get_gpu_memory()
        results.append(result)
        print(f"  -> {result['throughput_tps']:.1f} tok/s, "
              f"median {result['latency_median_ms']:.0f}ms\n")

    # Print comparison
    print("=" * 55)
    print("  RESULTS")
    print("=" * 55)
    print(f"{'Metric':<25} {'Full (FP16)':>15} {'Quant (AWQ)':>15}")
    print("-" * 55)

    full, quant = results[0], results[1]
    rows = [
        ("Throughput (tok/s)", f"{full['throughput_tps']:.1f}", f"{quant['throughput_tps']:.1f}"),
        ("Latency median (ms)", f"{full['latency_median_ms']:.0f}", f"{quant['latency_median_ms']:.0f}"),
        ("Latency P95 (ms)", f"{full['latency_p95_ms']:.0f}", f"{quant['latency_p95_ms']:.0f}"),
        ("Total tokens", str(full["total_tokens"]), str(quant["total_tokens"])),
    ]
    for label, v1, v2 in rows:
        print(f"{label:<25} {v1:>15} {v2:>15}")

    if quant["latency_median_ms"] > 0:
        speedup = full["latency_median_ms"] / quant["latency_median_ms"]
        print(f"\nSpeedup: {speedup:.2f}x faster with quantization")

    # Save results
    output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "benchmark_comparison.json")
    with open(output_path, "w") as f:
        json.dump({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "models": results}, f, indent=2)
    print(f"\nDetailed results: {output_path}")


if __name__ == "__main__":
    main()
