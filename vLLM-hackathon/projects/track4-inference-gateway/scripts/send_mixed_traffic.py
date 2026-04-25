"""
Drive the Inference Gateway with mixed traffic and report per-backend counts.

--multi-model: alternates between two distinct models
--ab-split:    sends requests for the SAME model name; observe how the gateway
               splits them across v1 / v2 pools based on configured weights

Assumes `kubectl port-forward -n llm-d svc/llm-d-gateway 8000:8000` is already
running so the gateway is reachable at http://localhost:8000.
"""

import argparse
import collections
import subprocess
import time
from typing import Dict

import httpx


GATEWAY = "http://localhost:8000"


def pull_backend_counts() -> Dict[str, int]:
    """Parse gateway /metrics for per-backend request counts."""
    try:
        text = httpx.get(f"{GATEWAY}/metrics", timeout=3).text
    except httpx.HTTPError:
        return {}
    counts: Dict[str, int] = collections.defaultdict(int)
    for line in text.splitlines():
        # Assumed metric name — adjust to the gateway's actual label scheme
        if line.startswith("llm_d_gateway_requests_total{"):
            # e.g. llm_d_gateway_requests_total{backend="llama-8b-v1"} 42
            try:
                label_kv = line[line.index("{")+1:line.index("}")]
                backend = [kv for kv in label_kv.split(",")
                           if kv.startswith("backend=")][0].split('"')[1]
                counts[backend] = int(float(line.split()[-1]))
            except (ValueError, IndexError):
                continue
    return dict(counts)


def send(model: str) -> None:
    httpx.post(f"{GATEWAY}/v1/chat/completions", json={
        "model": model,
        "messages": [{"role": "user", "content": "Say hi in 3 words."}],
        "max_tokens": 10,
        "temperature": 0.0,
    }, timeout=30)


def run_multi_model(n: int) -> None:
    models = [
        "meta-llama/Llama-3.1-8B-Instruct",
        "RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8",
    ]
    before = pull_backend_counts()
    for i in range(n):
        send(models[i % 2])
    time.sleep(2)
    after = pull_backend_counts()
    print_delta(before, after)


def run_ab(n: int) -> None:
    # Same model name — the gateway's weighted routing decides which pool.
    for _ in range(n):
        send("meta-llama/Llama-3.1-8B-Instruct")
    time.sleep(2)
    counts = pull_backend_counts()
    total = sum(counts.values()) or 1
    print("\nObserved A/B split:")
    for backend, count in counts.items():
        print(f"  {backend:<24}  {count:4d}  ({100*count/total:5.1f}%)")


def print_delta(before: Dict[str, int], after: Dict[str, int]) -> None:
    print("\nRequest counts (delta since start):")
    keys = sorted(set(before) | set(after))
    for k in keys:
        d = after.get(k, 0) - before.get(k, 0)
        print(f"  {k:<24}  +{d}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--multi-model", action="store_true")
    parser.add_argument("--ab-split", action="store_true")
    parser.add_argument("-n", type=int, default=100, help="Request count")
    args = parser.parse_args()

    if args.multi_model:
        run_multi_model(args.n)
    elif args.ab_split:
        run_ab(args.n)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
