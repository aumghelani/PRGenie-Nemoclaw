"""Run the Subject Agent N times in baseline mode and N times in optimized mode."""
from __future__ import annotations

import asyncio
import json
import statistics
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from subject_agent.agent import AgentConfig, SubjectAgent
from subject_agent.telemetry import TelemetryCollector
from .tasks import BenchmarkTask, get_task


@dataclass
class BenchmarkConfig:
    mode: str  # "baseline" | "optimized"
    base_url: str = "http://localhost:5000/v1"
    model: str = "nemotron"
    repeats: int = 3
    # nvext headers — only set in "optimized" mode by default
    nvext_priority: str | None = None
    nvext_predicted_osl: int | None = None
    nvext_latency_sensitive: bool | None = None
    output_dir: str = "traces"


@dataclass
class BenchmarkResult:
    task_id: str
    mode: str
    repeats: int
    runs: list[dict[str, Any]]
    aggregate: dict[str, Any]


class BenchmarkRunner:
    def __init__(self, config: BenchmarkConfig) -> None:
        self.config = config
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)

    def _agent_config(self) -> AgentConfig:
        return AgentConfig(
            base_url=self.config.base_url,
            model=self.config.model,
            nvext_priority=self.config.nvext_priority,
            nvext_predicted_osl=self.config.nvext_predicted_osl,
            nvext_latency_sensitive=self.config.nvext_latency_sensitive,
        )

    async def run_one(self, task: BenchmarkTask) -> dict[str, Any]:
        collector = TelemetryCollector(mode=self.config.mode)
        agent = SubjectAgent(self._agent_config(), collector)
        result = await agent.run(task.query)
        return result["trace"]

    async def run_task(self, task_id: str) -> BenchmarkResult:
        task = get_task(task_id)
        traces: list[dict[str, Any]] = []
        for i in range(self.config.repeats):
            t0 = time.perf_counter()
            trace = await self.run_one(task)
            wall = time.perf_counter() - t0
            trace["wall_seconds"] = wall
            traces.append(trace)
            print(f"  [{self.config.mode}] run {i+1}/{self.config.repeats} — {wall:.2f}s")

        agg = _aggregate(traces)
        result = BenchmarkResult(
            task_id=task_id,
            mode=self.config.mode,
            repeats=self.config.repeats,
            runs=traces,
            aggregate=agg,
        )
        path = Path(self.config.output_dir) / f"{task_id}__{self.config.mode}.json"
        path.write_text(json.dumps(asdict(result), indent=2))
        print(f"  wrote {path}")
        return result


def _aggregate(traces: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = [t["summary"] for t in traces if t.get("summary")]
    if not summaries:
        return {}

    def med(key: str) -> float | None:
        vals = [s[key] for s in summaries if s.get(key) is not None]
        return statistics.median(vals) if vals else None

    return {
        "median_total_ms": med("total_ms"),
        "median_avg_ttft_ms": med("avg_ttft_ms"),
        "median_decode_tps": med("decode_throughput_tps"),
        "median_input_tokens": med("total_input_tokens"),
        "median_output_tokens": med("total_output_tokens"),
        "n_llm_calls": summaries[0].get("llm_calls"),
        "n_tool_calls": summaries[0].get("tool_calls"),
    }


def compare(baseline: BenchmarkResult, optimized: BenchmarkResult) -> dict[str, Any]:
    """Produce the headline before/after table for the demo."""
    b = baseline.aggregate
    o = optimized.aggregate

    def speedup(b_val: float | None, o_val: float | None) -> float | None:
        if not b_val or not o_val or o_val == 0:
            return None
        return b_val / o_val

    return {
        "task_id": baseline.task_id,
        "metrics": {
            "total_ms": {
                "baseline": b.get("median_total_ms"),
                "optimized": o.get("median_total_ms"),
                "speedup": speedup(b.get("median_total_ms"), o.get("median_total_ms")),
            },
            "avg_ttft_ms": {
                "baseline": b.get("median_avg_ttft_ms"),
                "optimized": o.get("median_avg_ttft_ms"),
                "speedup": speedup(
                    b.get("median_avg_ttft_ms"), o.get("median_avg_ttft_ms")
                ),
            },
            "decode_tps": {
                "baseline": b.get("median_decode_tps"),
                "optimized": o.get("median_decode_tps"),
                "speedup": speedup(
                    o.get("median_decode_tps"), b.get("median_decode_tps")
                ),  # higher is better, flip
            },
        },
    }


async def run_compare(task_id: str, base_url: str, model: str, repeats: int = 3) -> dict[str, Any]:
    """Convenience: run baseline THEN optimized and emit a comparison report.

    NOTE: this assumes the SAME vLLM endpoint can be reconfigured between
    runs (or you point base_url at two different ports).  In practice on
    hackathon day you'd run two vLLM servers — one on port 5000 (baseline)
    and one on 5001 (optimized) — and pass two URLs.
    """
    baseline = await BenchmarkRunner(
        BenchmarkConfig(mode="baseline", base_url=base_url, model=model, repeats=repeats)
    ).run_task(task_id)

    optimized = await BenchmarkRunner(
        BenchmarkConfig(
            mode="optimized",
            base_url=base_url,
            model=model,
            repeats=repeats,
            nvext_priority="high",
            nvext_latency_sensitive=True,
        )
    ).run_task(task_id)

    report = compare(baseline, optimized)
    out_path = Path(BenchmarkConfig(mode="").output_dir) / f"{task_id}__compare.json"
    out_path.write_text(json.dumps(report, indent=2))
    return report
