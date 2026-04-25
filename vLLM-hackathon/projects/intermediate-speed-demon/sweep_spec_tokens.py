"""
Sweep --num-speculative-tokens across values 1-9 and collect results.

For each value of K, starts a vLLM server with speculative decoding,
runs a benchmark, shuts down the server, and moves to the next K.
Results are saved to results/sweep_k{N}.json for each value.

Usage:
    python3 sweep_spec_tokens.py
    python3 sweep_spec_tokens.py --k-values 1 3 5 7 --num-requests 30
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
TARGET_MODEL = "/models/llama-3.1-70b-instruct"
DRAFT_MODEL = "/models/llama-3.1-8b-instruct"
PORT = 8000


def wait_for_server(port: int, timeout: int = 180) -> bool:
    """Wait for vLLM server to become healthy."""
    import httpx

    for _ in range(timeout):
        try:
            r = httpx.get(f"http://localhost:{port}/health", timeout=5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def start_server(k: int) -> subprocess.Popen:
    """Start vLLM with speculative decoding for a given K."""
    cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", TARGET_MODEL,
        "--speculative-model", DRAFT_MODEL,
        "--num-speculative-tokens", str(k),
        "--tensor-parallel-size", "2",
        "--host", "0.0.0.0",
        "--port", str(PORT),
        "--max-model-len", "4096",
        "--gpu-memory-utilization", "0.90",
        "--dtype", "auto",
    ]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_benchmark(k: int, num_requests: int) -> str:
    """Run the workload benchmark and return the output path."""
    output_path = os.path.join(RESULTS_DIR, f"sweep_k{k}.json")
    cmd = [
        sys.executable, os.path.join(SCRIPT_DIR, "run_workload_bench.py"),
        "--port", str(PORT),
        "--model", TARGET_MODEL,
        "--num-requests", str(num_requests),
        "--workloads", os.path.join(SCRIPT_DIR, "workloads.json"),
        "--output", output_path,
        "--tag", f"speculative_k{k}",
    ]
    subprocess.run(cmd, check=True)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Sweep speculative token counts")
    parser.add_argument(
        "--k-values", type=int, nargs="+", default=[1, 3, 5, 7, 9],
        help="Values of K (num-speculative-tokens) to test",
    )
    parser.add_argument("--num-requests", type=int, default=30)
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("=" * 50)
    print("  Speed Demon — Speculative Token Sweep")
    print(f"  K values: {args.k_values}")
    print(f"  Requests per workload: {args.num_requests}")
    print("=" * 50)

    summary = {}

    for k in args.k_values:
        print(f"\n--- K={k} ---")

        # Start server
        print(f"  Starting server with --num-speculative-tokens {k}...")
        proc = start_server(k)

        if not wait_for_server(PORT):
            print(f"  ERROR: Server failed to start for K={k}, skipping.")
            proc.kill()
            proc.wait()
            continue

        print("  Server ready. Running benchmark...")

        try:
            output_path = run_benchmark(k, args.num_requests)

            # Load results for summary
            with open(output_path) as f:
                data = json.load(f)
            summary[k] = {
                workload_name: {
                    "throughput_tps": w["aggregate_throughput_tps"],
                    "latency_median_ms": w["latency_median_ms"],
                }
                for workload_name, w in data["workloads"].items()
            }
        finally:
            print("  Stopping server...")
            os.kill(proc.pid, signal.SIGTERM)
            proc.wait()
            # Brief pause to release GPU memory
            time.sleep(5)

    # Write sweep summary
    summary_path = os.path.join(RESULTS_DIR, "sweep_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 50}")
    print("  Sweep complete!")
    print(f"  Summary: {summary_path}")
    print(f"  Individual results: {RESULTS_DIR}/sweep_k*.json")
    print(f"\n  Run 'python3 plot_results.py' to generate charts.")
    print("=" * 50)


if __name__ == "__main__":
    main()
