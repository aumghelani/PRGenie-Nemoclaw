"""
Workload benchmark runner for Speed Demon.

Sends requests from workload profiles to a running vLLM server,
measures latency and throughput, and writes structured results to JSON.

Usage:
    python3 run_workload_bench.py \
        --port 8000 \
        --model /models/llama-3.1-70b-instruct \
        --num-requests 50 \
        --workloads workloads.json \
        --output results/baseline.json \
        --tag baseline
"""

import argparse
import json
import statistics
import time

import httpx


def run_single_request(
    url: str, model: str, prompt: str, max_tokens: int
) -> dict:
    """Send a single chat completion request and measure timing."""
    start = time.perf_counter()
    r = httpx.post(
        url,
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        },
        timeout=300,
    )
    elapsed = time.perf_counter() - start
    r.raise_for_status()
    data = r.json()

    usage = data["usage"]
    return {
        "latency_s": elapsed,
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "tokens_per_sec": usage["completion_tokens"] / elapsed if elapsed > 0 else 0,
    }


def run_workload(
    url: str,
    model: str,
    workload: dict,
    num_requests: int,
) -> dict:
    """Run a full workload and aggregate metrics."""
    prompts = workload["prompts"]
    max_tokens = workload["max_tokens"]
    results = []

    print(f"  Workload: {workload['name']} ({workload['description']})")
    print(f"    max_tokens={max_tokens}, requests={num_requests}")

    for i in range(num_requests):
        prompt = prompts[i % len(prompts)]
        result = run_single_request(url, model, prompt, max_tokens)
        results.append(result)
        if (i + 1) % 10 == 0:
            print(f"    [{i + 1}/{num_requests}] completed")

    latencies = [r["latency_s"] for r in results]
    tps_values = [r["tokens_per_sec"] for r in results]
    total_tokens = sum(r["completion_tokens"] for r in results)
    total_time = sum(latencies)

    return {
        "workload": workload["name"],
        "num_requests": num_requests,
        "max_tokens": max_tokens,
        "total_completion_tokens": total_tokens,
        "total_time_s": total_time,
        "aggregate_throughput_tps": total_tokens / total_time if total_time > 0 else 0,
        "latency_mean_ms": statistics.mean(latencies) * 1000,
        "latency_median_ms": statistics.median(latencies) * 1000,
        "latency_p95_ms": sorted(latencies)[int(0.95 * len(latencies))] * 1000,
        "latency_p99_ms": sorted(latencies)[int(0.99 * len(latencies))] * 1000,
        "tps_mean": statistics.mean(tps_values),
        "tps_median": statistics.median(tps_values),
        "individual_results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Workload benchmark runner")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", required=True)
    parser.add_argument("--num-requests", type=int, default=50)
    parser.add_argument("--workloads", required=True, help="Path to workloads.json")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--tag", default="unknown", help="Label for this run")
    args = parser.parse_args()

    url = f"http://localhost:{args.port}/v1/chat/completions"

    with open(args.workloads) as f:
        workload_config = json.load(f)

    print(f"\nBenchmark tag: {args.tag}")
    print(f"Model: {args.model}")
    print(f"Requests per workload: {args.num_requests}")
    print(f"Workloads: {len(workload_config['workloads'])}\n")

    all_results = {
        "tag": args.tag,
        "model": args.model,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "workloads": {},
    }

    for workload in workload_config["workloads"]:
        result = run_workload(url, args.model, workload, args.num_requests)
        all_results["workloads"][workload["name"]] = result
        print(
            f"    => {workload['name']}: "
            f"{result['aggregate_throughput_tps']:.1f} tok/s, "
            f"median latency {result['latency_median_ms']:.0f}ms\n"
        )

    with open(args.output, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
