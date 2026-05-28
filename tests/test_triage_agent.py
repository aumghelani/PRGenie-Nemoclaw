"""Phase 10 — Triage Agent."""
from __future__ import annotations

import pytest

from backend.agents.triage_agent import (
    DIFF_TRUNCATION_MARKER,
    _truncate_diff,
    analyze_pr,
    format_check_run_summary,
    format_triage_comment,
)
from backend.llm.client import LLMClient


@pytest.fixture
def llm():
    return LLMClient(mock_mode=True, base_url="http://x", model="nemotron")


def _ctx():
    persona = {
        "focus": ["correctness", "tests"], "tone": "constructive but direct",
        "strictness": 0.8, "common_phrases": ["edge cases?"],
    }
    trust = {"trust_level": "medium", "trust_score": 0.55, "signals": {"merge_rate": 0.6}}
    risk = {
        "risk_level": "high", "risk_score": 0.7,
        "sensitive_files": ["requirements.txt"], "diff_size": 160, "should_escalate": False,
    }
    pr_data = {
        "pr_number": 42,
        "pr_title": "Add Redis cache",
        "author": "octocontributor",
        "files": [
            {"filename": "app/cache.py"},
            {"filename": "requirements.txt"},
        ],
        "additions": 142,
        "deletions": 18,
        "diff": "diff --git a/app/cache.py b/app/cache.py\n+import redis\n",
    }
    return persona, trust, risk, pr_data


def test_truncate_diff_keeps_short_diffs_intact():
    short = "x" * 1000
    assert _truncate_diff(short) == short


def test_truncate_diff_inserts_marker_for_long_diffs():
    long = "A" * 2000 + "B" * 2000
    out = _truncate_diff(long)
    assert DIFF_TRUNCATION_MARKER in out
    assert out.startswith("A" * 100)
    assert out.endswith("B" * 100)


async def test_analyze_pr_returns_mock_triage(llm):
    persona, trust, risk, pr_data = _ctx()
    out = await analyze_pr(pr_data, persona, trust, risk, suggested_reviewer="maintainer-jane", llm=llm)
    assert out["priority"] == "high"
    assert out["suggested_action"] == "request_changes"
    assert "Redis" in out["summary"]


async def test_analyze_pr_records_nvext_high_priority(llm):
    persona, trust, risk, pr_data = _ctx()
    await analyze_pr(pr_data, persona, trust, risk, "maintainer-jane", llm)
    rec = llm.recorded_calls[-1]
    assert rec.headers["x-nvext-priority"] == "high"
    assert rec.headers["x-nvext-request-class"] == "agent.first"


def test_format_triage_comment_includes_disclosure():
    persona, trust, risk, pr_data = _ctx()
    analysis = {
        "summary": "Adds Redis cache.",
        "priority": "high",
        "concerns": ["No TTL"],
        "checklist": ["Add TTL"],
    }
    body = format_triage_comment(analysis, trust, risk, "maintainer-jane")
    # NemoClaw will check for AI disclosure markers.
    assert "PRGenie" in body
    assert "AI-assisted" in body
    # Trust + risk visible.
    assert "medium" in body
    assert "high" in body
    # Reviewer mention.
    assert "@maintainer-jane" in body
    # Concerns + checklist rendered.
    assert "No TTL" in body
    assert "Add TTL" in body


def test_format_triage_comment_handles_missing_reviewer():
    persona, trust, risk, pr_data = _ctx()
    analysis = {"summary": "x", "priority": "low", "concerns": [], "checklist": []}
    body = format_triage_comment(analysis, trust, risk, suggested_reviewer=None)
    assert "no clear owner" in body


def test_format_check_run_summary_compact():
    persona, trust, risk, pr_data = _ctx()
    analysis = {"summary": "x", "priority": "high", "concerns": ["A"], "checklist": []}
    out = format_check_run_summary(analysis, trust, risk)
    assert "Trust" in out and "Risk" in out and "Priority" in out
