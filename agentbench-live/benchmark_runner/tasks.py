"""Benchmark tasks — multi-part research questions sized to exercise the
4-LLM-call loop and produce 4-8 tool invocations.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BenchmarkTask:
    id: str
    title: str
    query: str
    expected_tool_calls: int
    notes: str = ""


BENCHMARK_TASKS: list[BenchmarkTask] = [
    BenchmarkTask(
        id="econ-three-countries",
        title="Compare economic policies of three countries",
        query=(
            "Compare the current monetary policies of the United States, "
            "the European Union, and Japan. For each, identify the policy rate, "
            "the central bank's stated stance, and one major risk factor."
        ),
        expected_tool_calls=6,
        notes="Demo headline task — judges see this one.",
    ),
    BenchmarkTask(
        id="ai-chips-2026",
        title="Survey AI accelerator chips launched in 2026",
        query=(
            "List the major AI accelerator chips announced or launched in 2026. "
            "For each, capture the vendor, peak FLOPs, memory capacity, and a "
            "headline customer."
        ),
        expected_tool_calls=5,
    ),
    BenchmarkTask(
        id="rag-vs-finetuning",
        title="When to choose RAG over fine-tuning",
        query=(
            "Summarize the trade-offs between RAG and fine-tuning for enterprise "
            "LLM deployment. Cover update frequency, latency, accuracy, and cost. "
            "Cite at least 3 sources."
        ),
        expected_tool_calls=4,
    ),
    BenchmarkTask(
        id="vllm-features",
        title="Which vLLM optimizations matter for agents",
        query=(
            "Which vLLM optimizations have the largest impact on agentic workloads? "
            "Rank by expected speedup and explain the mechanism for each."
        ),
        expected_tool_calls=4,
        notes="Self-referential — fun for the demo.",
    ),
    BenchmarkTask(
        id="boston-coffee",
        title="Plan a coffee tour of the Seaport",
        query=(
            "Recommend a 4-stop coffee tour of Boston's Seaport district. For each "
            "stop, give the address, signature drink, and walking distance to the "
            "next stop."
        ),
        expected_tool_calls=8,
        notes="Light demo task to test under concurrent load.",
    ),
]


def get_task(task_id: str) -> BenchmarkTask:
    for t in BENCHMARK_TASKS:
        if t.id == task_id:
            return t
    raise KeyError(f"unknown task: {task_id}")
