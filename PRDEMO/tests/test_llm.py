"""
Phase 4 tests — LLM client + prompts + mock responses.

We do NOT hit a real vLLM endpoint here. The mock-mode path exercises the
full client surface; the nvext-header logic is tested independently.
"""
from __future__ import annotations

import pytest

from backend.config import settings
from backend.llm.client import (
    LLMClient,
    build_nvext_headers,
)
from backend.llm.mock_responses import (
    MOCK_BY_TOOL,
    MOCK_PERSONA,
    MOCK_REVIEW,
    MOCK_TRIAGE,
)
from backend.llm import prompts


@pytest.fixture
def client():
    return LLMClient(mock_mode=True, base_url="http://unused", model="nemotron")


# ---------------------------------------------------------------------------
# Mock-mode tool calls
# ---------------------------------------------------------------------------


async def test_complete_tool_returns_mock_triage(client):
    out = await client.complete_tool(
        system=prompts.SYSTEM_TRIAGE,
        user="anything",
        tool=prompts.TRIAGE_TOOL,
    )
    assert out == MOCK_TRIAGE
    assert out["priority"] in {"high", "medium", "low"}
    assert "Redis" in out["summary"]


async def test_complete_tool_returns_mock_persona(client):
    out = await client.complete_tool(
        system=prompts.SYSTEM_PERSONA, user="x", tool=prompts.PERSONA_TOOL,
    )
    assert out == MOCK_PERSONA
    assert "edge cases?" in out["common_phrases"]


async def test_complete_tool_returns_mock_review(client):
    out = await client.complete_tool(
        system=prompts.SYSTEM_REVIEW, user="x", tool=prompts.REVIEW_TOOL,
    )
    assert out == MOCK_REVIEW
    assert out["verdict"] in {"COMMENT", "REQUEST_CHANGES"}
    assert all({"path", "line", "body"} <= c.keys() for c in out["comments"])


async def test_complete_tool_returns_mock_clusters(client):
    out = await client.complete_tool(
        system=prompts.SYSTEM_CLUSTER, user="x", tool=prompts.CLUSTER_TOOL,
    )
    assert "clusters" in out
    assert any(c["id"] == "login-special-chars" for c in out["clusters"])


async def test_recorded_calls_capture_headers_and_response(client):
    await client.complete_tool(system="sys", user="usr", tool=prompts.TRIAGE_TOOL)
    rec = client.recorded_calls[-1]
    assert rec.tool_name == "submit_triage"
    assert rec.system == "sys"
    assert rec.user == "usr"
    assert rec.response == MOCK_TRIAGE
    # Default settings have ENABLE_NVEXT_HEADERS=True
    assert "x-nvext-priority" in rec.headers


async def test_unknown_tool_raises(client):
    fake_tool = {"type": "function", "function": {"name": "does_not_exist", "parameters": {}}}
    with pytest.raises(KeyError):
        await client.complete_tool(system="x", user="y", tool=fake_tool)


# ---------------------------------------------------------------------------
# nvext headers
# ---------------------------------------------------------------------------


def test_nvext_triage_is_high_priority_first_call():
    h = build_nvext_headers("submit_triage")
    assert h["x-nvext-priority"] == "high"
    assert h["x-nvext-request-class"] == "agent.first"
    assert h["x-nvext-latency-sensitive"] == "1"
    assert int(h["x-nvext-predicted-osl"]) > 0


def test_nvext_review_is_high_priority_final_call():
    h = build_nvext_headers("submit_review")
    assert h["x-nvext-priority"] == "high"
    assert h["x-nvext-request-class"] == "agent.final"
    assert h["x-nvext-latency-sensitive"] == "1"


def test_nvext_persona_is_low_priority_background():
    h = build_nvext_headers("submit_persona")
    assert h["x-nvext-priority"] == "low"
    assert h["x-nvext-request-class"] == "agent.background"
    assert h["x-nvext-latency-sensitive"] == "0"


def test_nvext_clusters_is_low_priority_batch():
    h = build_nvext_headers("submit_clusters")
    assert h["x-nvext-priority"] == "low"
    assert h["x-nvext-request-class"] == "agent.batch"


def test_nvext_disabled_returns_empty(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_NVEXT_HEADERS", False)
    h = build_nvext_headers("submit_triage")
    assert h == {}


def test_nvext_explicit_latency_override():
    h = build_nvext_headers("submit_persona", latency_sensitive=True)
    assert h["x-nvext-latency-sensitive"] == "1"


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------


def test_triage_prompt_formats_with_pr_context():
    body = prompts.USER_TRIAGE.format(
        focus="['correctness']",
        tone="constructive",
        strictness=0.8,
        common_phrases="['edge cases?']",
        trust_level="medium",
        trust_score=0.55,
        trust_signals="{'merge_rate': 0.6}",
        risk_level="high",
        risk_score=0.7,
        sensitive_files="['requirements.txt']",
        suggested_reviewer="@maintainer-jane",
        pr_number=42,
        pr_title="Add Redis cache",
        author="octocontributor",
        files_count=4,
        files_list="app/cache.py, app/users.py, requirements.txt, tests/test_users.py",
        additions=142,
        deletions=18,
        diff="diff --git ...",
    )
    assert "PR #42" in body
    assert "@octocontributor" in body
    assert "constructive" in body
    assert "submit_triage" in body


def test_all_tool_schemas_have_required_fields():
    for tool in (prompts.TRIAGE_TOOL, prompts.PERSONA_TOOL, prompts.REVIEW_TOOL, prompts.CLUSTER_TOOL):
        fn = tool["function"]
        assert "name" in fn and "parameters" in fn
        params = fn["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params and len(params["required"]) > 0


def test_mock_by_tool_covers_every_tool_schema():
    schema_names = {
        prompts.TRIAGE_TOOL["function"]["name"],
        prompts.PERSONA_TOOL["function"]["name"],
        prompts.REVIEW_TOOL["function"]["name"],
        prompts.CLUSTER_TOOL["function"]["name"],
    }
    assert schema_names == set(MOCK_BY_TOOL.keys())
