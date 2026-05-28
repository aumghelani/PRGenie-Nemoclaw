"""Phase 13 — Issue Demand Agent."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.agents.issue_demand_agent import (
    cluster_issues,
    format_demand_comment,
    score_and_persist,
    score_issue,
)
from backend.db.session import init_engine, get_session
from backend.db.store import upsert_issue_score
from backend.llm.client import LLMClient

REPO = "acme/widgets"


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    init_engine(f"sqlite:///{tmp_path / 'demand.db'}")


@pytest.fixture
def llm():
    return LLMClient(mock_mode=True, base_url="http://x", model="nemotron")


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat().replace("+00:00", "Z")


def test_score_high_for_popular_old_bug():
    s = score_issue({
        "number": 1, "title": "x", "body": "y",
        "reactions": 30, "comments": 12, "labels": ["bug"],
        "created_at": _days_ago(45),
    })
    assert s["demand_level"] == "high"
    assert s["priority_score"] >= 8.0
    assert s["days_open"] >= 40


def test_score_low_for_quiet_new_issue():
    s = score_issue({
        "number": 2, "title": "x", "body": "y",
        "reactions": 0, "comments": 0, "labels": [],
        "created_at": _days_ago(0),
    })
    assert s["demand_level"] == "low"


def test_security_label_outweighs_bug():
    high_sec = score_issue({"number": 3, "title": "x", "body": "y", "reactions": 5, "comments": 2, "labels": ["security"], "created_at": _days_ago(10)})
    high_bug = score_issue({"number": 4, "title": "x", "body": "y", "reactions": 5, "comments": 2, "labels": ["bug"], "created_at": _days_ago(10)})
    assert high_sec["demand_score"] > high_bug["demand_score"]


def test_neglect_score_grows_with_silence():
    s_recent = score_issue(
        {"number": 5, "title": "x", "body": "y", "reactions": 5, "comments": 2, "labels": [], "created_at": _days_ago(20)},
        last_maintainer_response_at=_days_ago(1),
    )
    s_silent = score_issue(
        {"number": 6, "title": "x", "body": "y", "reactions": 5, "comments": 2, "labels": [], "created_at": _days_ago(20)},
        last_maintainer_response_at=_days_ago(20),
    )
    assert s_silent["neglect_score"] > s_recent["neglect_score"]
    assert s_silent["priority_score"] > s_recent["priority_score"]


async def test_score_and_persist_writes_row():
    issue = {"number": 7, "title": "x", "body": "y", "reactions": 30, "comments": 12, "labels": ["bug"], "created_at": _days_ago(45)}
    s = await score_and_persist(REPO, issue)
    assert s["demand_level"] == "high"


async def test_cluster_issues_assigns_ids(llm):
    # Seed three unclustered issues.
    with get_session() as ses:
        for n in (88, 91, 95):
            upsert_issue_score(ses, n, REPO, {
                "demand_score": 5.0, "neglect_score": 1.0, "priority_score": 5.0, "demand_level": "medium",
            })

    issues_by_number = {
        88: {"title": "Login fails for emails with +", "body": "..."},
        91: {"title": "Redis cache eviction missing", "body": "..."},
        95: {"title": "Login fails on unicode email", "body": "..."},
    }

    clusters = await cluster_issues(REPO, issues_by_number, llm, min_cluster_size=2)
    assert len(clusters) >= 1
    # Mock returns login-special-chars cluster grouping 88+95.
    cluster_ids = {c["id"] for c in clusters}
    assert "login-special-chars" in cluster_ids


def test_format_demand_comment_includes_disclosure_and_label():
    score = {"reactions": 12, "unique_commenters": 3, "days_open": 14, "demand_level": "high", "neglect_score": 2.0, "priority_score": 8.0}
    body = format_demand_comment(score)
    assert "AI-assisted" in body
    assert "demand:high" in body


def test_format_demand_comment_with_cluster():
    score = {"reactions": 12, "unique_commenters": 3, "days_open": 14, "demand_level": "high", "neglect_score": 0.5, "priority_score": 8.0}
    cluster = {"id": "x", "name": "Cache bugs", "issue_numbers": [88, 95], "summary": "All cache-related"}
    body = format_demand_comment(score, cluster)
    assert "#88" in body and "#95" in body
    assert "Cache bugs" in body
