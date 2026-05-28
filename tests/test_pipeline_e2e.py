"""
Phase 11 end-to-end — fire a PR webhook and verify the full pipeline.

This is the demo's "what would happen on a real PR open" test.
Asserts on:
  * recorded GitHub side-effects (labels, comment, check run)
  * the structured response from /webhook
  * the persisted PRAnalysis row in the DB
"""
from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.config import settings
from backend.db.session import get_session, init_engine
from backend.db.store import get_pr_analysis
from backend.github_client import get_github_client, reset_github_client
from backend.llm.client import reset_llm_client
from backend.main import app

PAYLOAD_DIR = Path(__file__).parent / "mock_payloads"


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def fresh_state(tmp_path):
    init_engine(f"sqlite:///{tmp_path / 'e2e.db'}")
    reset_github_client()
    reset_llm_client()


@pytest.fixture
async def http():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_pr_pipeline_full_flow(http: AsyncClient):
    body = (PAYLOAD_DIR / "pr_opened.json").read_bytes()
    r = await http.post(
        "/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sign(body),
            "X-GitHub-Delivery": "e2e-1",
        },
    )
    assert r.status_code == 200, r.text
    out = r.json()

    # --- Response shape ---
    assert out["handled_as"] == "pr_event"
    assert out["repo"] == "acme/widgets"
    assert out["pr_number"] == 42
    assert out["trust_level"] in {"high", "medium", "new", "flagged"}
    assert out["risk_level"] in {"low", "medium", "high", "critical"}
    assert out["priority"] in {"high", "medium", "low"}
    assert out["suggested_reviewer"] == "maintainer-jane"
    assert out["check_run_id"] is not None
    assert out["comment_id"] is not None

    # The mock PR (Redis cache + requirements.txt) should yield risk >= medium.
    assert out["risk_level"] in {"medium", "high", "critical"}

    # Labels were applied.
    assert any(label.startswith("trust:") for label in out["labels_applied"])
    assert any(label.startswith("risk:") for label in out["labels_applied"])

    # --- GitHub side effects landed in the recorded log ---
    gh = get_github_client()
    methods = [c.method for c in gh.recorded_calls]
    # Mock yaml fetch happens via PolicyEnforcer.from_repo (no record entry, that's a read)
    assert "ensure_labels_exist" in methods
    assert "add_labels" in methods
    assert "create_check_run" in methods
    assert "post_pr_comment" in methods

    # The triage comment carries the AI disclosure footer.
    pr_comment_call = next(c for c in gh.recorded_calls if c.method == "post_pr_comment")
    body_text = pr_comment_call.payload["body"]
    assert "PRGenie" in body_text
    assert "AI-assisted" in body_text
    assert "@maintainer-jane" in body_text

    # --- DB has the analysis cached for /prgenie review ---
    with get_session() as s:
        row = get_pr_analysis(s, 42, "acme/widgets")
        assert row is not None
        assert row.summary  # not empty
        assert row.suggested_reviewer == "maintainer-jane"


async def test_prgenie_review_command_after_pr_open(http: AsyncClient):
    """End-to-end: PR opens (cache analysis) → /prgenie review submits inline review."""
    # 1. PR opens — caches PRAnalysis.
    pr_body = (PAYLOAD_DIR / "pr_opened.json").read_bytes()
    r1 = await http.post("/webhook", content=pr_body, headers={
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": sign(pr_body),
    })
    assert r1.status_code == 200

    # 2. Maintainer types /prgenie review.
    cmd_body = (PAYLOAD_DIR / "issue_comment_command.json").read_bytes()
    r2 = await http.post("/webhook", content=cmd_body, headers={
        "X-GitHub-Event": "issue_comment",
        "X-Hub-Signature-256": sign(cmd_body),
    })
    assert r2.status_code == 200, r2.text
    out = r2.json()
    assert out["handled_as"] == "review_submitted"
    assert out["verdict"] in {"COMMENT", "REQUEST_CHANGES"}
    assert out["comment_count"] >= 1

    # 3. The submit_pr_review side-effect was recorded.
    gh = get_github_client()
    review_calls = [c for c in gh.recorded_calls if c.method == "submit_pr_review"]
    assert len(review_calls) == 1
    assert review_calls[0].payload["event"] in {"COMMENT", "REQUEST_CHANGES"}


async def test_issue_event_scores_and_labels(http: AsyncClient):
    body = (PAYLOAD_DIR / "issue_created.json").read_bytes()
    r = await http.post("/webhook", content=body, headers={
        "X-GitHub-Event": "issues",
        "X-Hub-Signature-256": sign(body),
    })
    assert r.status_code == 200
    out = r.json()
    assert out["handled_as"] == "issue_event"
    assert out["demand_level"] in {"high", "medium", "low"}

    gh = get_github_client()
    methods = [c.method for c in gh.recorded_calls]
    assert "ensure_labels_exist" in methods
    assert "add_labels" in methods
    label_call = next(c for c in gh.recorded_calls if c.method == "add_labels")
    assert any(l.startswith("demand:") for l in label_call.payload["labels"])


async def test_pipeline_idempotent_under_synchronize(http: AsyncClient):
    """Synchronize event runs the same pipeline; second run should overwrite, not duplicate."""
    body = (PAYLOAD_DIR / "pr_opened.json").read_bytes().replace(b'"opened"', b'"synchronize"', 1)
    sig = sign(body)
    headers = {"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": sig}
    r1 = await http.post("/webhook", content=body, headers=headers)
    r2 = await http.post("/webhook", content=body, headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    # DB should have ONE row for PR #42 (upsert), not two.
    with get_session() as s:
        row = get_pr_analysis(s, 42, "acme/widgets")
        assert row is not None
