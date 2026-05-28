"""
GitHub webhook receiver.

POST /webhook
  - Verifies X-Hub-Signature-256 against GITHUB_WEBHOOK_SECRET
  - Parses X-GitHub-Event header
  - Hands off to webhook_handler.route_event(event_type, payload)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Header, HTTPException, Request

from backend.config import settings
from backend import webhook_handler

log = logging.getLogger("prclaw.router")
router = APIRouter()


def verify_signature(body: bytes, signature_header: str | None, secret: str) -> bool:
    """
    GitHub sends `sha256=<hex>` in X-Hub-Signature-256.
    Compare with HMAC-SHA256(secret, body) using constant-time compare.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    sent = signature_header.split("=", 1)[1].strip()
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sent, digest)


@router.post("/webhook")
async def webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
):
    body = await request.body()

    if not verify_signature(body, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET):
        log.warning("webhook signature mismatch (delivery=%s)", x_github_delivery)
        raise HTTPException(status_code=401, detail="invalid signature")

    if not x_github_event:
        raise HTTPException(status_code=400, detail="missing X-GitHub-Event header")

    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"invalid json: {e}")

    result = await webhook_handler.route_event(x_github_event, payload)
    return result
