"""
Profile a live vLLM server to find hot Python/CUDA functions.

Uses py-spy (no code changes to vLLM required). Samples the vLLM API server
process for the configured duration and emits a flamegraph SVG.

Usage:
    python3 profile_vllm.py --duration 120 --output profile.svg

Pair this with a load generator running in another terminal:
    guidellm run --config scenarios/chat.yaml
"""

import argparse
import subprocess
import sys
import time


def find_vllm_pid() -> int:
    """Find the PID of the running vLLM API server."""
    try:
        out = subprocess.check_output(
            ["pgrep", "-f", "vllm.entrypoints.openai.api_server"],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        print("✗ No vLLM API server process found. Is it running?", file=sys.stderr)
        sys.exit(1)
    pids = out.splitlines()
    if len(pids) > 1:
        print(f"⚠ Multiple vLLM processes found ({pids}); profiling the first.", file=sys.stderr)
    return int(pids[0])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=60,
                        help="Seconds to sample (default: 60)")
    parser.add_argument("--output", default="profile.svg",
                        help="Output SVG path (default: profile.svg)")
    parser.add_argument("--rate", type=int, default=250,
                        help="Samples per second (default: 250)")
    args = parser.parse_args()

    pid = find_vllm_pid()
    print(f"Profiling vLLM PID={pid} for {args.duration}s → {args.output}")
    print("Tip: hit the server with a load generator now, or results will be mostly idle time.")

    subprocess.run([
        "py-spy", "record",
        "--pid", str(pid),
        "--duration", str(args.duration),
        "--rate", str(args.rate),
        "--output", args.output,
        "--format", "flamegraph",
    ], check=True)

    print(f"\n✓ Flamegraph written to {args.output}")
    print("  Open it in a browser — widest bars are your hot paths.")
    print("  Typical hot functions: attention kernels, sampling, scheduler.step(), KV-cache manager.")


if __name__ == "__main__":
    main()
