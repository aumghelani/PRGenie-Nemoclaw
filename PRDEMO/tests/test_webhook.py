"""
Phase 1 tests — webhook signature verification + event dispatch.

Run:
    pytest tests/test_webhook.py -v

These tests boot the FastAPI app in-process via httpx + ASGI transport, so
no real network or uvicorn needed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.config import settings
from backend.main import app

PAYLOAD_DIR = Path(__file__).parent / "mock_payloads"


def sign(body: bytes, secret: str = None) -> str:
    secret = secret or settings.GITHUB_WEBHOOK_SECRET
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def _post(client: AsyncClient, body: bytes, *, event: str, sig: str | None):
    headers = {"X-GitHub-Event": event, "X-GitHub-Delivery": "test-delivery-1"}
    if sig is not None:
        headers["X-Hub-Signature-256"] = sig
    return await client.post("/webhook", content=body, headers=headers)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_webhook_rejects_missing_signature(client: AsyncClient):
    body = b'{"action":"opened"}'
    r = await _post(client, body, event="pull_request", sig=None)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature(client: AsyncClient):
    body = b'{"action":"opened"}'
    r = await _post(client, body, event="pull_request", sig="sha256=deadbeef")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_webhook_pr_opened_dispatches(client: AsyncClient):
    body = (PAYLOAD_DIR / "pr_opened.json").read_bytes()
    r = await _post(client, body, event="pull_request", sig=sign(body))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["handled_as"] == "pr_event"
    assert data["repo"] == "acme/widgets"
    assert data["pr_number"] == 42
    assert data["action"] == "opened"


@pytest.mark.asyncio
async def test_webhook_issue_opened_dispatches(client: AsyncClient):
    body = (PAYLOAD_DIR / "issue_created.json").read_bytes()
    r = await _post(client, body, event="issues", sig=sign(body))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["handled_as"] == "issue_event"
    assert data["issue_number"] == 88


@pytest.mark.asyncio
async def test_webhook_command_dispatches(client: AsyncClient):
    """`/prgenie review` returns one of the review-handler outcomes
    (review_submitted if cached analysis exists, review_no_analysis otherwise)."""
    body = (PAYLOAD_DIR / "issue_comment_command.json").read_bytes()
    r = await _post(client, body, event="issue_comment", sig=sign(body))
    assert r.status_code == 200, r.text
    data = r.json()
    # Without a prior PR-opened event in this isolated test, no cached analysis exists.
    assert data["handled_as"] in {"review_submitted", "review_no_analysis"}


@pytest.mark.asyncio
async def test_webhook_non_command_issue_comment_ignored(client: AsyncClient):
    body = json.dumps({
        "action": "created",
        "comment": {"body": "thanks for the PR!"},
        "issue": {"number": 42},
        "repository": {"full_name": "acme/widgets"},
    }).encode()
    r = await _post(client, body, event="issue_comment", sig=sign(body))
    assert r.status_code == 200
    assert r.json()["handled_as"] == "issue_comment_ignored_non_command"


@pytest.mark.asyncio
async def test_webhook_ping_event(client: AsyncClient):
    body = json.dumps({"zen": "Keep it logically awesome.", "hook_id": 1}).encode()
    r = await _post(client, body, event="ping", sig=sign(body))
    assert r.status_code == 200
    assert r.json()["handled_as"] == "ping"


@pytest.mark.asyncio
async def test_webhook_unknown_event_safely_ignored(client: AsyncClient):
    body = b'{"action":"whatever"}'
    r = await _post(client, body, event="star", sig=sign(body))
    assert r.status_code == 200
    assert r.json()["handled_as"] == "ignored"
