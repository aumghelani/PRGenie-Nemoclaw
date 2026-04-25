"""CLI: run a benchmark task in optimized mode and dump the trace.

Assumes vLLM is started with prefix caching, FP8 KV, spec decoding flags
(use vllm_setup/04_serve_optimized.sh).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from benchmark_runner import BenchmarkConfig, BenchmarkRunner

load_dotenv()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--base-url", default=os.getenv("VLLM_BASE_URL", "http://localhost:5000/v1"))
    parser.add_argument("--model", default=os.getenv("VLLM_MODEL", "nemotron"))
    args = parser.parse_args()

    runner = BenchmarkRunner(
        BenchmarkConfig(
            mode="optimized",
            base_url=args.base_url,
            model=args.model,
            repeats=args.repeats,
            nvext_priority="high",
            nvext_latency_sensitive=True,
        )
    )
    result = await runner.run_task(args.task_id)
    print()
    print("optimized aggregate:", result.aggregate)


if __name__ == "__main__":
    asyncio.run(main())
