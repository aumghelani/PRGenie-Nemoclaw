"""
Phase 5 tests — Trust Scorer.

Three layers:
  1. Pure scorer: tests _compute_signals + _score_from_signals against
     hand-built histories. No mocks needed.
  2. Async flow: runs compute_trust() against a mock GitHubClient and an
     in-memory SQLite, verifies persistence + return shape.
  3. Cache hit: second call within the freshness window short-circuits
     and does NOT re-fetch GitHub.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import SQLModel

from backend.agents.trust_scorer import (
    _compute_signals,
    _score_from_signals,
    compute_trust,
)
from backend.db.session import get_session, init_engine
from backend.db.store import get_trust
from backend.github_client import GitHubClient

REPO = "acme/widgets"
INSTALL = 55555555


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Each test gets a fresh DB so cache state doesn't leak across tests."""
    init_engine(f"sqlite:///{tmp_path / 'trust.db'}")


@pytest.fixture
def gh():
    return GitHubClient(mock_mode=True, app_id="0", private_key_path="/x")


# ---------------------------------------------------------------------------
# Pure scoring
# ---------------------------------------------------------------------------


def _years_ago(years: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=int(365 * years))
    return dt.isoformat().replace("+00:00", "Z")


def test_signals_aggregate_basic():
    prs = [
        {"state": "closed", "merged": True,  "created_at": "2026-01-01T10:00:00Z", "merged_at": "2026-01-02T10:00:00Z"},
        {"state": "closed", "merged": True,  "created_at": "2026-02-01T10:00:00Z", "merged_at": "2026-02-02T10:00:00Z"},
        {"state": "closed", "merged": False, "created_at": "2026-03-01T10:00:00Z", "merged_at": None},
        {"state": "open",   "merged": False, "created_at": "2026-04-01T10:00:00Z", "merged_at": None},
    ]
    s = _compute_signals(prs, _years_ago(2))
    assert s["total_prs"] == 4
    assert s["merged_prs"] == 2
    assert s["closed_without_merge"] == 1
    assert s["merge_rate"] == 0.5
    assert s["account_age_days"] >= 360


def test_score_high_for_seasoned_contributor():
    signals = {
        "total_prs": 10, "merged_prs": 9, "merge_rate": 0.9,
        "account_age_days": 800, "avg_response_hours": 12.0,
        "resolved_changes": 8, "total_requested_changes": 10,
        "closed_without_merge": 0,
    }
    score, level = _score_from_signals(signals)
    assert level == "high"
    assert score >= 0.75


def test_score_medium_for_decent_contributor():
    signals = {
        "total_prs": 5, "merged_prs": 3, "merge_rate": 0.6,
        "account_age_days": 200, "avg_response_hours": 24.0,
        "resolved_changes": 0, "total_requested_changes": 0,
        "closed_without_merge": 1,
    }
    score, level = _score_from_signals(signals)
    assert level == "medium"
    assert 0.45 <= score < 0.75


def test_score_new_overrides_when_no_history():
    signals = {
        "total_prs": 0, "merged_prs": 0, "merge_rate": 0.0,
        "account_age_days": 30, "avg_response_hours": 24.0,
        "resolved_changes": 0, "total_requested_changes": 0,
        "closed_without_merge": 0,
    }
    score, level = _score_from_signals(signals)
    assert level == "new"


def test_score_flagged_for_low_merge_rate_with_history():
    signals = {
        "total_prs": 10, "merged_prs": 1, "merge_rate": 0.1,
        "account_age_days": 10, "avg_response_hours": 200.0,
        "resolved_changes": 0, "total_requested_changes": 5,
        "closed_without_merge": 9,
    }
    score, level = _score_from_signals(signals)
    assert level == "flagged"
    assert score < 0.45


def test_score_clamps_to_unit_interval():
    s = {"total_prs": 1, "merged_prs": 1, "merge_rate": 1.0,
         "account_age_days": 10000, "avg_response_hours": 0.001,
         "resolved_changes": 100, "total_requested_changes": 100, "closed_without_merge": 0}
    score, level = _score_from_signals(s)
    assert 0.0 <= score <= 1.0
    assert level == "high"


# ---------------------------------------------------------------------------
# Async flow against mock GitHub
# ---------------------------------------------------------------------------


async def test_compute_trust_fetches_persists_returns(gh):
    out = await compute_trust("octocontributor", REPO, gh, INSTALL)
    assert out["login"] == "octocontributor"
    assert out["trust_level"] in {"high", "medium", "new", "flagged"}
    assert 0.0 <= out["trust_score"] <= 1.0
    assert "merge_rate" in out["signals"]
    assert out["cached"] is False

    with get_session() as s:
        row = get_trust(s, "octocontributor", REPO)
        assert row is not None
        assert row.trust_score == out["trust_score"]


async def test_compute_trust_uses_cache_on_second_call(gh, monkeypatch):
    out1 = await compute_trust("octocontributor", REPO, gh, INSTALL)
    assert out1["cached"] is False

    # Sabotage the GitHub client. If cache hits, this never runs → no error.
    async def boom(*a, **k):
        raise AssertionError("cache should have prevented the GitHub call")
    monkeypatch.setattr(gh, "get_contributor_prs", boom)
    monkeypatch.setattr(gh, "get_user", boom)

    out2 = await compute_trust("octocontributor", REPO, gh, INSTALL, cache_hours=24.0)
    assert out2["cached"] is True
    assert out2["trust_level"] == out1["trust_level"]
    assert out2["trust_score"] == out1["trust_score"]


async def test_compute_trust_recomputes_when_cache_stale(gh):
    await compute_trust("octocontributor", REPO, gh, INSTALL)

    # Force the row to look 48h old.
    with get_session() as s:
        row = get_trust(s, "octocontributor", REPO)
        row.updated_at = datetime.now() - timedelta(hours=48)
        s.add(row)
        s.commit()

    out = await compute_trust("octocontributor", REPO, gh, INSTALL, cache_hours=24.0)
    assert out["cached"] is False  # re-computed


async def test_compute_trust_for_unknown_contributor(gh, monkeypatch):
    """Brand new user with no PRs → 'new'."""
    async def empty_prs(*a, **k):
        return []
    monkeypatch.setattr(gh, "get_contributor_prs", empty_prs)

    out = await compute_trust("brand-new-user", REPO, gh, INSTALL)
    assert out["trust_level"] == "new"
    assert out["signals"]["total_prs"] == 0
