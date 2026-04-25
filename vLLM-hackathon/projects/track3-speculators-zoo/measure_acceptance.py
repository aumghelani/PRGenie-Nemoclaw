"""
Measure acceptance rate and end-to-end throughput for each speculation strategy.

Expects that you start each serve_configs/*.sh one at a time (or drive this
script with a helper that cycles through them).

Usage:
    # After starting one config (e.g. bash serve_configs/eagle.sh):
    python3 measure_acceptance.py --label eagle

    # Drive the whole matrix — starts/stops each server in turn:
    python3 measure_acceptance.py --all
"""

import argparse
import csv
import json
import os
import statistics
import subprocess
import time
from pathlib import Path

import httpx


CONFIGS = ["no_speculation", "ngram", "draft_model", "eagle", "medusa"]
VLLM_URL = "http://localhost:8000"
MODEL = "/models/llama-3.1-70b-instruct"

# Mixed workload to exercise different acceptance-rate regimes.
WORKLOAD = (
    ["Write a Python function to compute the nth Fibonacci number."] * 20 +
    ["Explain gravity in one paragraph."] * 20 +
    ["Summarize these 3 sentences: The quick brown fox jumps. It was a dark night. Hello world."] * 20
)


def wait_for_server(timeout: int = 180) -> None:
    for _ in range(timeout):
        try:
            if httpx.get(f"{VLLM_URL}/health", timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise TimeoutError(f"vLLM did not become ready within {timeout}s")


def measure(label: str) -> dict:
    print(f"  Warming up...")
    # One warmup request so the first measurement isn't cold-start
    httpx.post(f"{VLLM_URL}/v1/chat/completions", json={
        "model": MODEL,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 16,
    }, timeout=60)

    latencies = []
    total_out_toks = 0
    accepted_draft_toks = 0
    total_draft_toks = 0

    t0 = time.time()
    for prompt in WORKLOAD:
        rstart = time.time()
        r = httpx.post(f"{VLLM_URL}/v1/chat/completions", json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 256,
            "temperature": 0.0,
        }, timeout=180)
        r.raise_for_status()
        elapsed = time.time() - rstart
        body = r.json()
        latencies.append(elapsed)
        total_out_toks += body["usage"]["completion_tokens"]

    wall = time.time() - t0

    # Pull acceptance stats from vLLM /metrics if available
    try:
        metrics_text = httpx.get(f"{VLLM_URL}/metrics", timeout=5).text
        for line in metrics_text.splitlines():
            if line.startswith("vllm:spec_decode_num_accepted_tokens"):
                accepted_draft_toks = float(line.split()[-1])
            elif line.startswith("vllm:spec_decode_num_draft_tokens"):
                total_draft_toks = float(line.split()[-1])
    except httpx.HTTPError:
        pass

    accept_rate = (accepted_draft_toks / total_draft_toks) if total_draft_toks > 0 else None

    result = {
        "config": label,
        "requests": len(WORKLOAD),
        "wall_s": round(wall, 2),
        "throughput_tok_s": round(total_out_toks / wall, 1),
        "latency_p50_s": round(statistics.median(latencies), 3),
        "latency_p99_s": round(sorted(latencies)[int(0.99 * len(latencies))], 3),
        "acceptance_rate": round(accept_rate, 3) if accept_rate is not None else "n/a",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", help="Label for this measurement (e.g. 'eagle')")
    parser.add_argument("--all", action="store_true", help="Drive the full matrix")
    parser.add_argument("--output", default="results/acceptance_rates.csv")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    if args.all:
        for cfg in CONFIGS:
            print(f"\n=== {cfg} ===")
            print(f"  Starting serve_configs/{cfg}.sh...")
            server = subprocess.Popen(
                ["bash", f"serve_configs/{cfg}.sh"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                wait_for_server()
                results.append(measure(cfg))
            finally:
                server.terminate()
                server.wait(timeout=30)
            time.sleep(5)
    elif args.label:
        results.append(measure(args.label))
    else:
        parser.print_help()
        return

    # Write CSV
    if results:
        with out_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            w.writeheader()
            w.writerows(results)
        print(f"\n✓ Written to {out_path}")
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
