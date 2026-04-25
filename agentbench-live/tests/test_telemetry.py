"""Unit tests for telemetry primitives — these don't need a vLLM endpoint."""
from __future__ import annotations

import time

from subject_agent.telemetry import TelemetryCollector


def test_span_lifecycle():
    c = TelemetryCollector()
    with c.span("outer", "agent") as s_outer:
        time.sleep(0.005)
        with c.span("inner", "llm", model="nemotron") as s_inner:
            c.annotate(ttft_ms=12.3, output_tokens=42, input_tokens=100)
        assert s_inner.duration_ms > 0
        assert s_inner.attrs["ttft_ms"] == 12.3
    assert s_outer.duration_ms > s_inner.duration_ms

    trace = c.to_trace()
    assert trace["mode"] == "baseline"
    assert len(trace["spans"]) == 2
    summary = trace["summary"]
    assert summary["llm_calls"] == 1
    assert summary["total_output_tokens"] == 42


def test_summary_decode_throughput():
    c = TelemetryCollector()
    with c.span("agent.run", "agent"):
        with c.span("llm.test", "llm"):
            time.sleep(0.01)
            c.annotate(ttft_ms=2.0, output_tokens=100)
    summary = c.to_trace()["summary"]
    assert summary["decode_throughput_tps"] is not None
    assert summary["decode_throughput_tps"] > 0
