"""
Speculation regression gate.

Measures current speedup (spec-enabled vs. baseline) on a fixed workload,
compares against a committed baseline, and exits non-zero if the speedup has
regressed beyond the threshold.

Designed to run in CI to catch vLLM updates that break speculative decoding.

Usage:
    # First time:
    python3 spec_regression_test.py --save regression/baseline.json

    # CI (fails build if speedup dropped > 15%):
    python3 spec_regression_test.py --baseline regression/baseline.json --threshold 0.15
"""

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx

VLLM_URL = "http://localhost:8000"
MODEL = "/models/llama-3.1-70b-instruct"

WORKLOAD = [
    "Write a Python function to sort a list of integers.",
    "Explain in one paragraph what an LLM is.",
    "Write a haiku about speculative decoding.",
] * 10


def measure() -> float:
    """Return observed tokens/sec for the fixed workload."""
    total_toks = 0
    t0 = time.time()
    for p in WORKLOAD:
        r = httpx.post(f"{VLLM_URL}/v1/chat/completions", json={
            "model": MODEL,
            "messages": [{"role": "user", "content": p}],
            "max_tokens": 128,
            "temperature": 0.0,
        }, timeout=120)
        r.raise_for_status()
        total_toks += r.json()["usage"]["completion_tokens"]
    return total_toks / (time.time() - t0)


def wait_health(timeout: int = 180):
    for _ in range(timeout):
        try:
            if httpx.get(f"{VLLM_URL}/health", timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise TimeoutError("vLLM not ready")


def run_full():
    """Start baseline, measure, stop. Start EAGLE, measure, stop. Compute speedup."""
    cwd = Path(__file__).parent.parent

    print("Measuring baseline (no speculation)...")
    baseline_proc = subprocess.Popen(
        ["bash", str(cwd / "serve_configs" / "no_speculation.sh")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        wait_health()
        baseline_tps = measure()
    finally:
        baseline_proc.terminate()
        baseline_proc.wait(timeout=30)
    time.sleep(5)

    print("Measuring EAGLE speculation...")
    eagle_proc = subprocess.Popen(
        ["bash", str(cwd / "serve_configs" / "eagle.sh")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        wait_health()
        eagle_tps = measure()
    finally:
        eagle_proc.terminate()
        eagle_proc.wait(timeout=30)

    speedup = eagle_tps / baseline_tps
    return {
        "baseline_tok_s": round(baseline_tps, 1),
        "eagle_tok_s": round(eagle_tps, 1),
        "speedup": round(speedup, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", help="Save current measurement as baseline")
    parser.add_argument("--baseline")
    parser.add_argument("--threshold", type=float, default=0.15,
                        help="Fail if speedup drops > this fraction (default: 0.15 = 15%)")
    args = parser.parse_args()

    result = run_full()
    print(json.dumps(result, indent=2))

    if args.save:
        Path(args.save).write_text(json.dumps(result, indent=2))
        print(f"✓ Baseline saved to {args.save}")
        return

    if not args.baseline:
        return

    baseline = json.loads(Path(args.baseline).read_text())
    if result["speedup"] < baseline["speedup"] * (1 - args.threshold):
        print(f"\n✗ Speedup regressed: {result['speedup']}× vs baseline {baseline['speedup']}× "
              f"(threshold {args.threshold*100:.0f}%)")
        sys.exit(1)
    print(f"\n✓ Speedup within tolerance: {result['speedup']}× vs baseline {baseline['speedup']}×")


if __name__ == "__main__":
    main()
