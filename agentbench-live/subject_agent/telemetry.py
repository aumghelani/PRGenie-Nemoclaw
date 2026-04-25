"""Telemetry primitives — NAT-style spans for LLM calls and tool invocations.

Every span has start/stop wall-clock timestamps plus structured attrs.
Spans are flushed as a JSON trace ready for the Optimizer Agent and dashboard.
"""
from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from typing import Any, Iterator


@dataclass
class Span:
    span_id: str
    parent_id: str | None
    name: str
    kind: str  # "llm" | "tool" | "agent"
    start_ms: float
    end_ms: float | None = None
    attrs: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.end_ms is None:
            return -1.0
        return self.end_ms - self.start_ms

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["duration_ms"] = self.duration_ms
        return d


class TelemetryCollector:
    """Thread-unsafe collector — one per agent run."""

    def __init__(self, run_id: str | None = None, mode: str = "baseline") -> None:
        self.run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
        self.mode = mode  # "baseline" | "optimized"
        self.spans: list[Span] = []
        self._stack: list[Span] = []
        self._t0 = time.perf_counter()

    def _now_ms(self) -> float:
        return (time.perf_counter() - self._t0) * 1000.0

    @contextmanager
    def span(self, name: str, kind: str, **attrs: Any) -> Iterator[Span]:
        parent_id = self._stack[-1].span_id if self._stack else None
        s = Span(
            span_id=uuid.uuid4().hex[:12],
            parent_id=parent_id,
            name=name,
            kind=kind,
            start_ms=self._now_ms(),
            attrs=dict(attrs),
        )
        self.spans.append(s)
        self._stack.append(s)
        try:
            yield s
        finally:
            s.end_ms = self._now_ms()
            self._stack.pop()

    def annotate(self, **attrs: Any) -> None:
        """Add attrs to the currently-open span."""
        if self._stack:
            self._stack[-1].attrs.update(attrs)

    def to_trace(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "spans": [s.to_dict() for s in self.spans],
            "summary": self._summary(),
        }

    def _summary(self) -> dict[str, Any]:
        if not self.spans:
            return {}
        llm_spans = [s for s in self.spans if s.kind == "llm"]
        tool_spans = [s for s in self.spans if s.kind == "tool"]
        ttfts = [s.attrs.get("ttft_ms") for s in llm_spans if s.attrs.get("ttft_ms")]
        return {
            "total_ms": max((s.end_ms or 0) for s in self.spans),
            "llm_calls": len(llm_spans),
            "tool_calls": len(tool_spans),
            "avg_ttft_ms": sum(ttfts) / len(ttfts) if ttfts else None,
            "total_input_tokens": sum(s.attrs.get("input_tokens", 0) for s in llm_spans),
            "total_output_tokens": sum(s.attrs.get("output_tokens", 0) for s in llm_spans),
            "decode_throughput_tps": _decode_throughput(llm_spans),
        }


def _decode_throughput(llm_spans: list[Span]) -> float | None:
    total_out = sum(s.attrs.get("output_tokens", 0) for s in llm_spans)
    decode_ms = sum(
        max(0.0, (s.duration_ms - s.attrs.get("ttft_ms", 0))) for s in llm_spans
    )
    if decode_ms <= 0:
        return None
    return total_out / (decode_ms / 1000.0)
