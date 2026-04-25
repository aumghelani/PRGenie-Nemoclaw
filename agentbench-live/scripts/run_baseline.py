"""CLI: run a benchmark task in baseline mode and dump the trace."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Make sibling packages importable when invoked as `python scripts/run_baseline.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from benchmark_runner import BenchmarkConfig, BenchmarkRunner

load_dotenv()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id", help="benchmark task id (see benchmark_runner/tasks.py)")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--base-url", default=os.getenv("VLLM_BASE_URL", "http://localhost:5000/v1"))
    parser.add_argument("--model", default=os.getenv("VLLM_MODEL", "nemotron"))
    args = parser.parse_args()

    runner = BenchmarkRunner(
        BenchmarkConfig(
            mode="baseline",
            base_url=args.base_url,
            model=args.model,
            repeats=args.repeats,
        )
    )
    result = await runner.run_task(args.task_id)
    print()
    print("baseline aggregate:", result.aggregate)


if __name__ == "__main__":
    asyncio.run(main())
