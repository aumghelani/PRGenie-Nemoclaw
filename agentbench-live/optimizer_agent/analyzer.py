"""Trace analyzer — derives critical path, parallelism gaps, and OSL stats."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CriticalPath:
    span_ids: list[str]
    total_ms: float
    bottleneck_span_id: str
    bottleneck_ms: float


@dataclass
class ParallelismOpportunity:
    span_ids: list[str]
    total_serial_ms: float
    parallel_ms_estimate: float  # max of the involved spans
    savings_ms: float


@dataclass
class TraceStats:
    total_ms: float
    n_llm_calls: int
    n_tool_calls: int
    avg_ttft_ms: float | None
    prefix_recompute_ms_estimate: float
    serial_tool_blocks: list[ParallelismOpportunity] = field(default_factory=list)


class TraceAnalyzer:
    def __init__(self, trace: dict[str, Any]) -> None:
        self.trace = trace
        self.spans = trace.get("spans", [])
        self._by_id = {s["span_id"]: s for s in self.spans}

    # ----------------------------------------------------------- critical path

    def critical_path(self) -> CriticalPath:
        """Rough heuristic: walk the agent.run span and sum sequential children.

        We define the critical path as the chain of children of agent.run
        sorted by start_ms, since the loop is mostly sequential except for
        the parallel tool fan-out.
        """
        agent_run = next((s for s in self.spans if s["name"] == "agent.run"), None)
        if not agent_run:
            return CriticalPath(span_ids=[], total_ms=0.0, bottleneck_span_id="", bottleneck_ms=0.0)

        children = sorted(
            (s for s in self.spans if s.get("parent_id") == agent_run["span_id"]),
            key=lambda s: s["start_ms"],
        )
        path = [agent_run["span_id"]] + [c["span_id"] for c in children]
        bottleneck = max(children, key=lambda s: s["duration_ms"], default=agent_run)
        return CriticalPath(
            span_ids=path,
            total_ms=agent_run["duration_ms"],
            bottleneck_span_id=bottleneck["span_id"],
            bottleneck_ms=bottleneck["duration_ms"],
        )

    # --------------------------------------------------------- parallelism gap

    def parallelism_opportunities(self) -> list[ParallelismOpportunity]:
        """Find tool spans that ran serially but have the same parent (independent)."""
        opportunities: list[ParallelismOpportunity] = []
        # Group tool spans by parent_id.
        from collections import defaultdict
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for s in self.spans:
            if s["kind"] == "tool":
                groups[s.get("parent_id") or "_root_"].append(s)

        for parent_id, tools in groups.items():
            if len(tools) < 2:
                continue
            tools = sorted(tools, key=lambda s: s["start_ms"])
            # If they don't overlap, they're serial — flag as an opportunity.
            serial = all(
                tools[i]["end_ms"] <= tools[i + 1]["start_ms"] + 1.0
                for i in range(len(tools) - 1)
            )
            if not serial:
                continue
            total = sum(t["duration_ms"] for t in tools)
            par_estimate = max(t["duration_ms"] for t in tools)
            opportunities.append(
                ParallelismOpportunity(
                    span_ids=[t["span_id"] for t in tools],
                    total_serial_ms=total,
                    parallel_ms_estimate=par_estimate,
                    savings_ms=total - par_estimate,
                )
            )
        return opportunities

    # --------------------------------------------------------- prefix recompute

    def prefix_recompute_estimate_ms(self) -> float:
        """Estimate ms wasted recomputing the system prefix on every LLM call.

        Assumes ~3 K-token shared prefix at ~100 tok/ms prefill = ~30 ms/call.
        Battle plan §5A says 200-800 ms per call at 8 K context — we use 250 ms
        as a midpoint for the demo when prefix caching is OFF.
        """
        llm_calls = [s for s in self.spans if s["kind"] == "llm"]
        per_call_ms = 250.0  # conservative midpoint
        return per_call_ms * max(0, len(llm_calls) - 1)

    # ------------------------------------------------------------------ stats

    def stats(self) -> TraceStats:
        summary = self.trace.get("summary", {})
        return TraceStats(
            total_ms=summary.get("total_ms", 0.0),
            n_llm_calls=summary.get("llm_calls", 0),
            n_tool_calls=summary.get("tool_calls", 0),
            avg_ttft_ms=summary.get("avg_ttft_ms"),
            prefix_recompute_ms_estimate=self.prefix_recompute_estimate_ms(),
            serial_tool_blocks=self.parallelism_opportunities(),
        )
