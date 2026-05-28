"""
Integration smoke test — exercises Phases 0-4 wired together.

Boot the FastAPI app in-process, fire a real signed webhook, and confirm
every subsystem (DB, GitHub client, LLM client, mock data) is reachable
from the same process without import or init errors.
"""
from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

from backend.config import settings
from backend.db.session import get_session, init_engine
from backend.db.store import save_pr_analysis, get_pr_analysis, upsert_trust, get_trust
from backend.github_client import GitHubClient
from backend.llm.client import LLMClient
from backend.llm import prompts
from backend.main import app

PAYLOAD_DIR = Path(__file__).parent / "mock_payloads"


def sign(body: bytes) -> str:
    digest = hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.fixture
async def app_client(tmp_path):
    init_engine(f"sqlite:///{tmp_path / 'integ.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_app_boots_and_health_reachable(app_client: AsyncClient):
    r = await app_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_webhook_pr_event_with_db_write(app_client: AsyncClient, tmp_path):
    """
    Simulate the full path that Phase 11 will eventually walk:
    webhook arrives → handler dispatches → we write a PRAnalysis row →
    fetch it back, confirm round-trip.
    """
    body = (PAYLOAD_DIR / "pr_opened.json").read_bytes()
    r = await app_client.post(
        "/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sign(body),
            "X-GitHub-Delivery": "integ-1",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["handled_as"] == "pr_event"
    assert data["repo"] == "acme/widgets"
    assert data["pr_number"] == 42

    # Same DB the app uses → write directly.
    with get_session() as s:
        save_pr_analysis(s, 42, "acme/widgets", {
            "trust_level": "medium", "risk_level": "high", "priority": "high",
            "summary": "Adds Redis cache.", "concerns": ["No TTL"], "checklist": ["Add TTL"],
        })
        row = get_pr_analysis(s, 42, "acme/widgets")
        assert row is not None
        assert row.summary == "Adds Redis cache."


async def test_github_and_llm_clients_cooperate_in_mock_mode():
    """
    Walk a slice of the future PR pipeline: fetch PR data via GitHubClient
    (mock), feed it into an LLMClient (mock) triage call, get structured JSON.
    """
    gh = GitHubClient(mock_mode=True, app_id="0", private_key_path="/x")
    llm = LLMClient(mock_mode=True, base_url="http://x", model="nemotron")

    files = await gh.get_pr_files("acme/widgets", 42, installation_id=1)
    diff = await gh.get_pr_diff("acme/widgets", 42, installation_id=1)
    assert any(f["filename"] == "requirements.txt" for f in files)
    assert "redis" in diff.lower()

    triage = await llm.complete_tool(
        system=prompts.SYSTEM_TRIAGE,
        user=prompts.USER_TRIAGE.format(
            focus="['correctness']", tone="constructive", strictness=0.8,
            common_phrases="['edge cases?']",
            trust_level="new", trust_score=0.1, trust_signals="{}",
            risk_level="high", risk_score=0.7, sensitive_files="['requirements.txt']",
            suggested_reviewer="@maintainer-jane",
            pr_number=42, pr_title="Add Redis cache", author="octocontributor",
            files_count=len(files),
            files_list=", ".join(f["filename"] for f in files),
            additions=142, deletions=18,
            diff=diff[:1500],
        ),
        tool=prompts.TRIAGE_TOOL,
    )
    assert triage["priority"] == "high"
    assert triage["suggested_action"] in {"approve", "request_changes", "comment", "escalate"}
    # The recorded call carries the nvext priority that NAT will route on.
    assert llm.recorded_calls[-1].headers["x-nvext-priority"] == "high"


async def test_github_writes_record_in_mock(app_client: AsyncClient):
    """A simulated write through GitHubClient should land in recorded_calls."""
    gh = GitHubClient(mock_mode=True, app_id="0", private_key_path="/x")
    await gh.add_labels("acme/widgets", 42, ["trust:medium", "risk:high"], installation_id=1)
    await gh.post_pr_comment("acme/widgets", 42, "🤖 PRClaw analysis ready.", installation_id=1)
    methods = [c.method for c in gh.recorded_calls]
    assert methods == ["add_labels", "post_pr_comment"]


async def test_trust_round_trip_through_real_session(app_client: AsyncClient):
    """The DB is the same one the app initialized in lifespan."""
    with get_session() as s:
        upsert_trust(s, "octocontributor", "acme/widgets", {
            "trust_level": "medium", "trust_score": 0.55,
            "signals": {"merge_rate": 0.6, "account_age_days": 237},
        })
        row = get_trust(s, "octocontributor", "acme/widgets")
        assert row is not None
        assert row.trust_score == 0.55
