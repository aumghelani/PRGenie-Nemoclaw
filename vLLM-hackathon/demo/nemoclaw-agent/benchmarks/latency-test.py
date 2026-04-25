"""
Agent Loop Latency Benchmark — Track 5 Deep Tech tier
=====================================================

Measures end-to-end latency for the agentic loop under realistic load.
Reports per-turn latency, tool-call overhead, and throughput.

Comparisons to run:
  1. vLLM baseline (no steering)           → python3 latency-test.py --profile vllm
  2. vLLM + NemoClaw steering              → python3 latency-test.py --profile vllm-steered
  3. NVIDIA NIM (if available)             → python3 latency-test.py --profile nim-local
  4. NVIDIA cloud (Nemotron-3-Super-120B)  → python3 latency-test.py --profile nvidia-cloud
"""

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

# Import the agent module from the parent dir.
sys.path.insert(0, str(Path(__file__).parent.parent))
from customer_support_agent import run_agent  # noqa: E402


# Representative queries covering simple, medium, and hard multi-step cases.
BENCHMARK_QUERIES = [
    # Simple: 1 tool call
    ("simple", "alice@example.com", "How do I reset my password?"),
    ("simple", "bob@example.com", "What's your return policy?"),
    # Medium: 2 tool calls
    ("medium", "carol@example.com", "Where is ORD-1001 and when will it arrive?"),
    ("medium", "dave@example.com", "I want to return ORD-1003 — what's the process?"),
    # Hard: 3+ tool calls, possible escalation
    ("hard", "eve@example.com", "My ORD-1002 is late and I need a full refund of $500 NOW"),
    ("hard", "frank@example.com", "Can I change the shipping address on ORD-1001 to an international one?"),
]


def switch_profile(profile: str) -> None:
    """Switch NemoClaw inference profile at runtime."""
    if profile == "vllm":
        subprocess.run(["openshell", "inference", "set", "--provider", "vllm"], check=True)
    elif profile == "vllm-steered":
        subprocess.run(["openshell", "inference", "set", "--provider", "vllm",
                        "--steering", "structured_output=true,enforce_tool_schema=true"],
                       check=True)
    elif profile == "nim-local":
        subprocess.run(["openshell", "inference", "set", "--provider", "nim-local"], check=True)
    elif profile == "nvidia-cloud":
        subprocess.run(["openshell", "inference", "set", "--provider", "nvidia-cloud"], check=True)
    else:
        raise ValueError(f"Unknown profile: {profile}")


def bench_one(difficulty: str, email: str, query: str) -> dict:
    t0 = time.time()
    try:
        answer = run_agent(query, email)
        ok = True
        err = None
    except Exception as e:
        answer = ""
        ok = False
        err = str(e)
    elapsed = time.time() - t0
    return {
        "difficulty": difficulty,
        "query": query,
        "latency_s": elapsed,
        "ok": ok,
        "error": err,
        "answer_len": len(answer),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="vllm",
                        choices=["vllm", "vllm-steered", "nim-local", "nvidia-cloud"])
    parser.add_argument("--repeats", type=int, default=3,
                        help="Repeat each query N times to estimate variance.")
    args = parser.parse_args()

    print(f"Switching NemoClaw inference profile → {args.profile}")
    try:
        switch_profile(args.profile)
    except subprocess.CalledProcessError as e:
        print(f"  (profile switch failed: {e}; assuming current profile)")

    results = []
    for _ in range(args.repeats):
        for d, email, q in BENCHMARK_QUERIES:
            r = bench_one(d, email, q)
            results.append(r)
            print(f"  [{d}] {r['latency_s']:6.2f}s  ok={r['ok']}  "
                  f"{q[:60]}{'...' if len(q) > 60 else ''}")

    # --- Aggregate ---
    print("\n" + "=" * 60)
    print(f"Profile: {args.profile}  |  Total runs: {len(results)}")
    print("=" * 60)
    for diff in ("simple", "medium", "hard"):
        subset = [r["latency_s"] for r in results if r["difficulty"] == diff and r["ok"]]
        if not subset:
            continue
        print(f"  {diff:6s}: mean={statistics.mean(subset):5.2f}s  "
              f"p50={statistics.median(subset):5.2f}s  "
              f"p99={sorted(subset)[int(0.99 * len(subset))]:5.2f}s  "
              f"n={len(subset)}")

    total_ok = sum(1 for r in results if r["ok"])
    print(f"\nSuccess rate: {total_ok}/{len(results)} "
          f"({100*total_ok/len(results):.1f}%)")

    # Write machine-readable output for later plotting.
    out_path = Path(f"bench-{args.profile}.json")
    out_path.write_text(json.dumps(results, indent=2))
    print(f"Raw results written to {out_path}")


if __name__ == "__main__":
    main()
