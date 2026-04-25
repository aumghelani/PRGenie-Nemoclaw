"""CLI: run baseline + optimized back-to-back and print the headline table."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from benchmark_runner.runner import run_compare

load_dotenv()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--base-url", default=os.getenv("VLLM_BASE_URL", "http://localhost:5000/v1"))
    parser.add_argument("--model", default=os.getenv("VLLM_MODEL", "nemotron"))
    args = parser.parse_args()

    print(f"Running {args.task_id} in baseline + optimized mode (n={args.repeats} each)…")
    report = await run_compare(args.task_id, args.base_url, args.model, repeats=args.repeats)
    print()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
