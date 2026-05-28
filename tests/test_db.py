"""
Phase 2 tests — DB models + store helpers.

Each test gets a fresh in-memory SQLite engine so tests are isolated.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from backend.db import models  # noqa: F401  (registers tables)
from backend.db.store import (
    analysis_to_dict,
    get_fresh_trust,
    get_high_demand_issues,
    get_persona,
    get_pr_analysis,
    get_trust,
    get_unclustered_issues,
    persona_to_dict,
    save_pr_analysis,
    set_cluster_ids,
    trust_to_dict,
    upsert_issue_score,
    upsert_persona,
    upsert_trust,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------


def test_persona_insert_and_read(session: Session):
    persona = upsert_persona(
        session,
        "acme/widgets",
        "maintainer-jane",
        {
            "focus": ["correctness", "tests"],
            "strictness": 0.8,
            "tone": "constructive but direct",
            "avg_comments_per_pr": 4.2,
            "common_phrases": ["edge cases?", "needs tests"],
            "tolerance": {"missing_tests": "low"},
        },
    )
    assert persona.id is not None

    fetched = get_persona(session, "acme/widgets")
    assert fetched is not None
    d = persona_to_dict(fetched)
    assert d["focus"] == ["correctness", "tests"]
    assert d["strictness"] == 0.8
    assert d["common_phrases"][0] == "edge cases?"
    assert d["tolerance"]["missing_tests"] == "low"


def test_persona_upsert_updates_existing(session: Session):
    upsert_persona(session, "acme/widgets", "jane", {"focus": ["a"], "strictness": 0.5})
    upsert_persona(session, "acme/widgets", "jane", {"focus": ["b", "c"], "strictness": 0.9})
    p = get_persona(session, "acme/widgets")
    d = persona_to_dict(p)
    assert d["focus"] == ["b", "c"]
    assert d["strictness"] == 0.9


# ---------------------------------------------------------------------------
# Trust
# ---------------------------------------------------------------------------


def test_trust_insert_and_read(session: Session):
    upsert_trust(
        session,
        "octocontributor",
        "acme/widgets",
        {"trust_level": "medium", "trust_score": 0.55, "signals": {"merge_rate": 0.6}},
    )
    t = get_trust(session, "octocontributor", "acme/widgets")
    assert t is not None
    d = trust_to_dict(t)
    assert d["trust_level"] == "medium"
    assert d["trust_score"] == 0.55
    assert d["signals"]["merge_rate"] == 0.6


def test_trust_upsert_overwrites(session: Session):
    upsert_trust(session, "u", "r/x", {"trust_level": "new", "trust_score": 0.1, "signals": {}})
    upsert_trust(session, "u", "r/x", {"trust_level": "high", "trust_score": 0.9, "signals": {}})
    t = get_trust(session, "u", "r/x")
    assert t.trust_level == "high"
    assert t.trust_score == 0.9


def test_trust_freshness_window(session: Session):
    upsert_trust(session, "u", "r/x", {"trust_level": "high", "trust_score": 0.8, "signals": {}})

    fresh = get_fresh_trust(session, "u", "r/x", max_age_hours=24)
    assert fresh is not None

    # Force the row to look stale
    row = get_trust(session, "u", "r/x")
    row.updated_at = datetime.now() - timedelta(hours=48)
    session.add(row)
    session.commit()

    stale = get_fresh_trust(session, "u", "r/x", max_age_hours=24)
    assert stale is None


# ---------------------------------------------------------------------------
# PRAnalysis
# ---------------------------------------------------------------------------


def test_pr_analysis_save_and_read(session: Session):
    save_pr_analysis(
        session,
        42,
        "acme/widgets",
        {
            "trust_level": "medium",
            "risk_level": "high",
            "priority": "high",
            "summary": "Adds Redis cache.",
            "concerns": ["No TTL", "Missing tests"],
            "checklist": ["Add TTL", "Cover invalidation"],
            "suggested_reviewer": "maintainer-jane",
            "suggested_action": "request_changes",
            "check_run_id": 999,
            "bot_comment_id": 12345,
        },
    )
    a = get_pr_analysis(session, 42, "acme/widgets")
    assert a is not None
    d = analysis_to_dict(a)
    assert d["risk_level"] == "high"
    assert d["concerns"] == ["No TTL", "Missing tests"]
    assert d["checklist"][0] == "Add TTL"
    assert d["check_run_id"] == 999


def test_pr_analysis_upsert(session: Session):
    save_pr_analysis(session, 42, "acme/widgets", {
        "trust_level": "new", "risk_level": "low", "priority": "low",
        "summary": "v1", "concerns": [], "checklist": [],
    })
    save_pr_analysis(session, 42, "acme/widgets", {
        "trust_level": "high", "risk_level": "medium", "priority": "high",
        "summary": "v2", "concerns": ["x"], "checklist": ["y"],
    })
    a = get_pr_analysis(session, 42, "acme/widgets")
    assert a.summary == "v2"
    assert a.priority == "high"


# ---------------------------------------------------------------------------
# IssueScore
# ---------------------------------------------------------------------------


def test_issue_score_and_high_demand_filter(session: Session):
    upsert_issue_score(session, 1, "acme/widgets", {
        "demand_score": 5.0, "neglect_score": 2.0, "priority_score": 10.0,
        "demand_level": "high", "reactions": 30, "unique_commenters": 8, "days_open": 14,
    })
    upsert_issue_score(session, 2, "acme/widgets", {
        "demand_score": 1.0, "neglect_score": 0.5, "priority_score": 0.5,
        "demand_level": "low", "reactions": 1, "unique_commenters": 1, "days_open": 1,
    })

    high = get_high_demand_issues(session, "acme/widgets", threshold=8.0)
    assert len(high) == 1
    assert high[0].issue_number == 1


def test_issue_clustering(session: Session):
    for n in (10, 11, 12):
        upsert_issue_score(session, n, "acme/widgets", {
            "demand_score": 2.0, "neglect_score": 1.0, "priority_score": 2.0,
            "demand_level": "low",
        })

    unclustered = get_unclustered_issues(session, "acme/widgets")
    assert len(unclustered) == 3

    set_cluster_ids(session, [
        (10, "acme/widgets", "redis-bug"),
        (11, "acme/widgets", "redis-bug"),
    ])

    unclustered_after = get_unclustered_issues(session, "acme/widgets")
    assert len(unclustered_after) == 1
    assert unclustered_after[0].issue_number == 12


# ---------------------------------------------------------------------------
# Lifespan integration
# ---------------------------------------------------------------------------


def test_init_engine_creates_tables(tmp_path):
    """init_engine() should make a usable DB at the given URL."""
    from backend.db.session import init_engine, get_session

    db_path = tmp_path / "test_lifespan.db"
    init_engine(f"sqlite:///{db_path}")
    with get_session() as s:
        upsert_trust(s, "u", "r/x", {"trust_level": "new", "trust_score": 0.1, "signals": {}})
        assert get_trust(s, "u", "r/x") is not None
