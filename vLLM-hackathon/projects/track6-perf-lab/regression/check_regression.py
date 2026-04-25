"""
Performance regression gate.

Runs a short GuideLLM workload, compares against a committed baseline, and
exits non-zero if any metric has regressed beyond the configured threshold.

Usage:
    # First time — save current perf as baseline:
    python3 check_regression.py --save baseline.json

    # Subsequent runs (CI):
    python3 check_regression.py --baseline baseline.json --threshold 0.10
"""

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx


VLLM_URL = "http://localhost:8000/v1/chat/completions"
MODEL = "/models/llama-3.1-8b-instruct"

# Fixed workload for reproducibility — don't change this between baseline + check.
WORKLOAD_PROMPTS = [
    "Explain transformers in 3 sentences.",
    "Write a Python function to reverse a linked list.",
    "Summarize: quantum computing uses qubits...",
    "What's the capital of France?",
    "Translate 'hello world' to Japanese.",
] * 10  # 50 requests total


def measure() -> dict:
    """Run the fixed workload and return a metric dict."""
    latencies = []
    ttfts = []
    total_tokens = 0
    t0 = time.time()

    for prompt in WORKLOAD_PROMPTS:
        req_start = time.time()
        r = httpx.post(VLLM_URL, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 128,
            "temperature": 0.0,
            "stream": False,
        }, timeout=60)
        elapsed = time.time() - req_start
        r.raise_for_status()
        body = r.json()
        latencies.append(elapsed)
        # TTFT would require streaming — approximate with first-token-latency=total/tokens
        ttfts.append(elapsed / max(body["usage"]["completion_tokens"], 1))
        total_tokens += body["usage"]["completion_tokens"]

    wall = time.time() - t0
    return {
        "total_requests": len(WORKLOAD_PROMPTS),
        "wall_seconds": wall,
        "throughput_tok_per_s": total_tokens / wall,
        "latency_p50_s": statistics.median(latencies),
        "latency_p99_s": sorted(latencies)[int(0.99 * len(latencies))],
        "approx_ttft_s": statistics.median(ttfts),
    }


def compare(baseline: dict, current: dict, threshold: float) -> list[str]:
    """Return list of regression strings; empty if all good."""
    failures = []
    # Lower-is-better metrics
    for m in ("latency_p50_s", "latency_p99_s", "approx_ttft_s"):
        if current[m] > baseline[m] * (1 + threshold):
            failures.append(f"{m}: {current[m]:.3f}s vs baseline {baseline[m]:.3f}s "
                            f"(+{100*(current[m]/baseline[m]-1):.1f}%)")
    # Higher-is-better metrics
    for m in ("throughput_tok_per_s",):
        if current[m] < baseline[m] * (1 - threshold):
            failures.append(f"{m}: {current[m]:.1f} vs baseline {baseline[m]:.1f} "
                            f"({100*(current[m]/baseline[m]-1):.1f}%)")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", help="Write measurement to this path as a new baseline")
    parser.add_argument("--baseline", help="Compare current perf against this file")
    parser.add_argument("--threshold", type=float, default=0.10,
                        help="Allowed regression fraction (default: 0.10 = 10%)")
    args = parser.parse_args()

    print("Measuring current performance...")
    current = measure()
    print(json.dumps(current, indent=2))

    if args.save:
        Path(args.save).write_text(json.dumps(current, indent=2))
        print(f"\n✓ Baseline written to {args.save}")
        return

    if not args.baseline:
        print("No --baseline given; nothing to compare against. Use --save to create one.")
        return

    baseline = json.loads(Path(args.baseline).read_text())
    failures = compare(baseline, current, args.threshold)

    if failures:
        print(f"\n✗ Regression detected (threshold: {args.threshold*100:.0f}%):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"\n✓ No regressions (all metrics within {args.threshold*100:.0f}% of baseline)")


if __name__ == "__main__":
    main()
