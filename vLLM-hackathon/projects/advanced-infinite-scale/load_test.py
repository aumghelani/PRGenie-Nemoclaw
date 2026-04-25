"""
Infinite Scale — Load Test with Ramping Concurrency

Sends requests to the llm-d gateway with increasing concurrency to observe
autoscaling behavior. Collects metrics at each concurrency level and produces
a JSON report.

Usage:
    # Port-forward the gateway first:
    kubectl port-forward -n llm-d svc/llm-d-gateway 8000:8000 &

    python3 load_test.py
    python3 load_test.py --gateway http://localhost:8000 --max-concurrency 16
"""

import argparse
import json
import os
import statistics
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

PROMPTS = [
    "Explain the concept of KV-cache in transformer inference and why it matters for memory efficiency.",
    "Write a Python implementation of a producer-consumer pattern using asyncio queues.",
    "Describe the differences between tensor parallelism and pipeline parallelism for distributed model inference.",
    "What are the trade-offs between prefill and decode phases in LLM serving? How does disaggregation help?",
    "Write a Kubernetes HPA configuration that scales based on custom Prometheus metrics.",
    "Explain how consistent hashing works and why it's useful for load balancing stateful inference workers.",
    "Compare gRPC and REST for inter-service communication in a microservices architecture.",
    "Write a Python decorator that retries a function with exponential backoff on specified exceptions.",
]


def send_request(
    gateway_url: str, model: str, prompt: str, max_tokens: int = 256
) -> dict:
    """Send a single request and return timing info."""
    start = time.perf_counter()
    try:
        r = httpx.post(
            f"{gateway_url}/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.1,
            },
            timeout=120,
        )
        r.raise_for_status()
        elapsed = time.perf_counter() - start
        data = r.json()
        return {
            "success": True,
            "latency_s": elapsed,
            "completion_tokens": data["usage"]["completion_tokens"],
            "prompt_tokens": data["usage"]["prompt_tokens"],
        }
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "success": False,
            "latency_s": elapsed,
            "error": str(e),
        }


def get_pod_count(namespace: str = "llm-d") -> dict:
    """Get current pod counts by component."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
            capture_output=True, text=True, timeout=10,
        )
        pods = json.loads(result.stdout).get("items", [])
        counts = {"prefill": 0, "decode": 0, "gateway": 0, "other": 0}
        for pod in pods:
            name = pod["metadata"]["name"]
            phase = pod["status"].get("phase", "Unknown")
            if phase != "Running":
                continue
            if "prefill" in name:
                counts["prefill"] += 1
            elif "decode" in name:
                counts["decode"] += 1
            elif "gateway" in name:
                counts["gateway"] += 1
            else:
                counts["other"] += 1
        return counts
    except Exception:
        return {"error": "kubectl unavailable"}


def run_concurrency_level(
    gateway_url: str,
    model: str,
    concurrency: int,
    requests_per_level: int,
) -> dict:
    """Run a batch of concurrent requests and aggregate results."""
    results = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(requests_per_level):
            prompt = PROMPTS[i % len(PROMPTS)]
            futures.append(executor.submit(send_request, gateway_url, model, prompt))

        for future in as_completed(futures):
            results.append(future.result())

    successes = [r for r in results if r.get("success")]
    failures = [r for r in results if not r.get("success")]

    latencies = [r["latency_s"] for r in successes]
    total_tokens = sum(r["completion_tokens"] for r in successes)
    total_time = max(latencies) if latencies else 0  # wall-clock ≈ slowest request

    return {
        "concurrency": concurrency,
        "total_requests": len(results),
        "successful": len(successes),
        "failed": len(failures),
        "total_tokens": total_tokens,
        "wall_clock_s": total_time,
        "throughput_tps": total_tokens / total_time if total_time > 0 else 0,
        "latency_mean_ms": statistics.mean(latencies) * 1000 if latencies else 0,
        "latency_median_ms": statistics.median(latencies) * 1000 if latencies else 0,
        "latency_p95_ms": (
            sorted(latencies)[int(0.95 * len(latencies))] * 1000 if latencies else 0
        ),
        "pod_counts": get_pod_count(),
    }


def main():
    parser = argparse.ArgumentParser(description="Ramping load test for llm-d")
    parser.add_argument("--gateway", default="http://localhost:8000")
    parser.add_argument("--model", default="/models/llama-3.1-70b-instruct")
    parser.add_argument(
        "--concurrency-levels", type=int, nargs="+", default=[1, 2, 4, 8, 16],
    )
    parser.add_argument("--requests-per-level", type=int, default=16)
    parser.add_argument("--settle-time", type=int, default=30,
                        help="Seconds to wait between levels for autoscaling")
    args = parser.parse_args()

    results_dir = os.path.join(SCRIPT_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)

    print("=" * 55)
    print("  Infinite Scale — Ramping Load Test")
    print(f"  Gateway: {args.gateway}")
    print(f"  Concurrency levels: {args.concurrency_levels}")
    print(f"  Requests per level: {args.requests_per_level}")
    print("=" * 55)

    all_results = []

    for level in args.concurrency_levels:
        print(f"\n--- Concurrency: {level} ---")
        result = run_concurrency_level(
            args.gateway, args.model, level, args.requests_per_level
        )
        all_results.append(result)

        print(f"  Successful: {result['successful']}/{result['total_requests']}")
        print(f"  Throughput: {result['throughput_tps']:.1f} tok/s")
        print(f"  Latency (median): {result['latency_median_ms']:.0f}ms")
        print(f"  Pods: {result['pod_counts']}")

        if level != args.concurrency_levels[-1]:
            print(f"  Waiting {args.settle_time}s for autoscaler to react...")
            time.sleep(args.settle_time)

    # Save results
    output_path = os.path.join(results_dir, "load_test_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "gateway": args.gateway,
            "model": args.model,
            "levels": all_results,
        }, f, indent=2)

    print(f"\n{'=' * 55}")
    print(f"  Results saved to: {output_path}")
    print(f"  Run 'python3 dashboard.py' for real-time monitoring")
    print("=" * 55)


if __name__ == "__main__":
    main()
