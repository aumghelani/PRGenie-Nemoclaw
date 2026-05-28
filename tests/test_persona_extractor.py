"""Phase 9 — Persona Extractor."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from backend.agents.persona_extractor import extract_persona, _format_reviews_for_prompt
from backend.db.session import get_session, init_engine
from backend.db.store import get_persona
from backend.github_client import GitHubClient
from backend.llm.client import LLMClient

REPO = "acme/widgets"
INSTALL = 1
LOGIN = "maintainer-jane"


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    init_engine(f"sqlite:///{tmp_path / 'persona.db'}")


@pytest.fixture
def gh():
    return GitHubClient(mock_mode=True, app_id="0", private_key_path="/x")


@pytest.fixture
def llm():
    return LLMClient(mock_mode=True, base_url="http://x", model="nemotron")


def test_format_reviews_packs_within_budget():
    reviews = [{"pr_number": i, "state": "COMMENTED", "body": "x" * 200} for i in range(20)]
    out = _format_reviews_for_prompt(reviews, char_budget=1000)
    assert len(out) <= 1100  # generous because each chunk has overhead


def test_format_reviews_handles_empty():
    out = _format_reviews_for_prompt([])
    assert "no reviews" in out


async def test_extract_persona_calls_llm_and_persists(gh, llm):
    out = await extract_persona(REPO, LOGIN, gh, llm, INSTALL)
    assert out["maintainer_login"] == LOGIN
    assert "edge cases?" in out["common_phrases"]
    assert out["strictness"] == 0.8
    assert out["cached"] is False

    with get_session() as s:
        row = get_persona(s, REPO)
        assert row is not None
        assert row.maintainer_login == LOGIN


async def test_extract_persona_uses_cache_within_window(gh, llm, monkeypatch):
    await extract_persona(REPO, LOGIN, gh, llm, INSTALL)

    async def boom(*a, **k):
        raise AssertionError("should have hit cache")
    monkeypatch.setattr(gh, "get_maintainer_reviews", boom)

    out = await extract_persona(REPO, LOGIN, gh, llm, INSTALL, refresh_days=7.0)
    assert out["cached"] is True


async def test_extract_persona_refreshes_when_stale(gh, llm):
    await extract_persona(REPO, LOGIN, gh, llm, INSTALL)

    with get_session() as s:
        row = get_persona(s, REPO)
        row.updated_at = datetime.now() - timedelta(days=10)
        s.add(row)
        s.commit()

    out = await extract_persona(REPO, LOGIN, gh, llm, INSTALL, refresh_days=7.0)
    assert out["cached"] is False
