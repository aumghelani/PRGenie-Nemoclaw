"""Unit tests for the optimizer — synthesizes a fake trace and checks recommendations."""
from __future__ import annotations

from optimizer_agent.analyzer import TraceAnalyzer
from optimizer_agent.recommender import Recommender


def _fake_trace() -> dict:
    # 4 LLM calls, 2 sibling tool calls that ran serially.
    return {
        "run_id": "fake",
        "mode": "baseline",
        "spans": [
            {"span_id": "a", "parent_id": None, "name": "agent.run", "kind": "agent",
             "start_ms": 0, "end_ms": 4000, "duration_ms": 4000, "attrs": {}},
            {"span_id": "b", "parent_id": "a", "name": "llm.plan", "kind": "llm",
             "start_ms": 0, "end_ms": 500, "duration_ms": 500,
             "attrs": {"ttft_ms": 300, "output_tokens": 50, "input_tokens": 1500}},
            {"span_id": "c", "parent_id": "a", "name": "tool:web_search", "kind": "tool",
             "start_ms": 500, "end_ms": 900, "duration_ms": 400, "attrs": {}},
            {"span_id": "d", "parent_id": "a", "name": "tool:web_search", "kind": "tool",
             "start_ms": 900, "end_ms": 1300, "duration_ms": 400, "attrs": {}},
            {"span_id": "e", "parent_id": "a", "name": "llm.synthesize", "kind": "llm",
             "start_ms": 1300, "end_ms": 2000, "duration_ms": 700,
             "attrs": {"ttft_ms": 350, "output_tokens": 80}},
            {"span_id": "f", "parent_id": "a", "name": "llm.gap_check", "kind": "llm",
             "start_ms": 2000, "end_ms": 2500, "duration_ms": 500,
             "attrs": {"ttft_ms": 280, "output_tokens": 40}},
            {"span_id": "g", "parent_id": "a", "name": "llm.final", "kind": "llm",
             "start_ms": 2500, "end_ms": 4000, "duration_ms": 1500,
             "attrs": {"ttft_ms": 320, "output_tokens": 200}},
        ],
        "summary": {
            "total_ms": 4000,
            "llm_calls": 4,
            "tool_calls": 2,
            "avg_ttft_ms": 312.5,
            "total_input_tokens": 1500,
            "total_output_tokens": 370,
            "decode_throughput_tps": 80.0,
        },
    }


def test_analyzer_finds_serial_tools():
    analyzer = TraceAnalyzer(_fake_trace())
    opps = analyzer.parallelism_opportunities()
    assert len(opps) == 1
    assert opps[0].savings_ms > 0  # 800 serial → 400 parallel


def test_recommender_emits_prefix_caching():
    analyzer = TraceAnalyzer(_fake_trace())
    recs = Recommender(analyzer).recommend()
    names = [r.name for r in recs]
    assert any("prefix caching" in n.lower() for n in names)
    assert any("speculative" in n.lower() for n in names)
