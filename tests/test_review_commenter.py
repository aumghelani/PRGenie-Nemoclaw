"""Phase 12 — Review Commenter."""
from __future__ import annotations

import pytest

from backend.agents.review_commenter import generate_review
from backend.llm.client import LLMClient
from backend.nemo_claw.policy_enforcer import PolicyEnforcer
from backend.nemo_claw.schemas import DEFAULT_POLICY


@pytest.fixture
def llm():
    return LLMClient(mock_mode=True, base_url="http://x", model="nemotron")


@pytest.fixture
def policy():
    return PolicyEnforcer(DEFAULT_POLICY)


async def test_generate_review_returns_constructive_comments(llm, policy):
    persona = {"focus": ["correctness"], "tone": "constructive but direct", "common_phrases": ["edge cases?"]}
    out = await generate_review("diff --git a/x.py b/x.py\n+x", persona, ["No TTL"], policy, llm)
    assert out["verdict"] in {"COMMENT", "REQUEST_CHANGES"}
    assert len(out["comments"]) >= 1
    for c in out["comments"]:
        assert {"path", "line", "body"} <= c.keys()


async def test_generate_review_blocks_approve_verdict(llm, policy, monkeypatch):
    """Even if the model returned APPROVE, code-side guardrail flips to COMMENT."""
    async def fake(*a, **kw):
        return {
            "comments": [{"path": "x.py", "line": 1, "body": "Looks reasonable to me overall."}],
            "verdict": "APPROVE",  # forbidden by policy + code guardrail
        }
    monkeypatch.setattr(llm, "complete_tool", fake)

    out = await generate_review("d", {}, [], policy, llm)
    assert out["verdict"] == "COMMENT"


async def test_generate_review_drops_harsh_comments(llm, policy, monkeypatch):
    async def fake(*a, **kw):
        return {
            "comments": [
                {"path": "x.py", "line": 1, "body": "This is stupid code, rewrite it."},
                {"path": "x.py", "line": 2, "body": "Consider extracting this into a helper for testability."},
                {"path": "x.py", "line": 3, "body": ""},  # empty, also dropped
            ],
            "verdict": "COMMENT",
        }
    monkeypatch.setattr(llm, "complete_tool", fake)

    out = await generate_review("d", {}, [], policy, llm)
    assert len(out["comments"]) == 1
    assert "extracting this into a helper" in out["comments"][0]["body"]
    reasons = [d["reason"] for d in out["dropped"]]
    assert any("harsh" in r for r in reasons)
    assert any("empty" in r for r in reasons)


async def test_generate_review_records_nvext_high_priority_final(llm, policy):
    await generate_review("diff", {}, [], policy, llm)
    rec = llm.recorded_calls[-1]
    assert rec.headers["x-nvext-request-class"] == "agent.final"
    assert rec.headers["x-nvext-priority"] == "high"
