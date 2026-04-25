"""
Webhook event router.

Receives parsed GitHub webhook events from routers/webhook.py and dispatches
to the right agent pipeline.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.agents.issue_demand_agent import (
    format_demand_comment,
    score_and_persist,
)
from backend.agents.persona_extractor import extract_persona
from backend.agents.review_commenter import generate_review
from backend.agents.reviewer_suggester import suggest_reviewer
from backend.agents.risk_agent import compute_risk
from backend.agents.triage_agent import (
    analyze_pr,
    format_check_run_summary,
    format_triage_comment,
)
from backend.agents.trust_scorer import compute_trust
from backend.db.session import get_session
from backend.db.store import (
    analysis_to_dict,
    get_persona,
    get_pr_analysis,
    persona_to_dict,
    save_pr_analysis,
)
from backend.github_client import get_github_client
from backend.llm.client import get_llm_client
from backend.nemo_claw.policy_enforcer import NemoClawViolation, PolicyEnforcer

log = logging.getLogger("prclaw.webhook")

LABEL_COLORS: dict[str, str] = {
    "trust:high":    "2ecc71", "trust:medium":  "f1c40f",
    "trust:new":     "95a5a6", "trust:flagged": "e74c3c",
    "risk:low":      "2ecc71", "risk:medium":   "e67e22",
    "risk:high":     "e74c3c", "risk:critical": "8e44ad",
    "demand:high":   "e74c3c", "demand:medium": "e67e22", "demand:low": "2ecc71",
}

# Event-action combinations we actually care about.
PR_ACTIONS = {"opened", "synchronize", "reopened"}
ISSUE_ACTIONS = {"opened", "edited", "reopened"}
COMMAND_PREFIX = "/prgenie"


async def route_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Top-level dispatcher. Returns a small dict for the HTTP response."""
    action = payload.get("action", "")
    log.info("event=%s action=%s", event_type, action)

    if event_type == "pull_request" and action in PR_ACTIONS:
        return await handle_pr_event(payload)

    if event_type == "issue_comment" and action == "created":
        body = (payload.get("comment", {}) or {}).get("body", "").strip()
        if body.startswith(COMMAND_PREFIX):
            return await handle_command(payload)
        return {"ok": True, "handled_as": "issue_comment_ignored_non_command"}

    if event_type == "issues" and action in ISSUE_ACTIONS:
        return await handle_issue_event(payload)

    if event_type == "pull_request_review" and action == "submitted":
        return await handle_review_ingestion(payload)

    if event_type == "ping":
        # GitHub sends this on app install / webhook test
        return {"ok": True, "handled_as": "ping", "zen": payload.get("zen")}

    return {"ok": True, "handled_as": "ignored", "event_type": event_type, "action": action}


# ---------------------------------------------------------------------------
# Stub handlers — real implementations land in later phases.
# ---------------------------------------------------------------------------


async def handle_pr_event(payload: dict) -> dict:
    """
    Full PR pipeline:
        Trust → Risk → Reviewer → Persona → Triage (LLM)
        → NemoClaw gate → Check Run + bot comment + labels → DB save
    """
    pr = payload["pull_request"]
    repo_full_name = payload["repository"]["full_name"]
    installation_id = payload["installation"]["id"]
    pr_number = pr["number"]
    author = pr["user"]["login"]

    github = get_github_client()
    llm = get_llm_client()

    # 1. Load NemoClaw policy.
    policy = await PolicyEnforcer.from_repo(repo_full_name, github, installation_id)

    # 2. Run rule-based agents in parallel (well, sequentially since they're cheap).
    trust = await compute_trust(
        author, repo_full_name, github, installation_id,
        cache_hours=policy.doc.trust.cache_hours,
    )
    files = await github.get_pr_files(repo_full_name, pr_number, installation_id)
    file_names = [f["filename"] for f in files]
    risk = compute_risk(
        file_names,
        pr["additions"], pr["deletions"],
        trust["trust_level"],
        extra_sensitive=policy.extra_sensitive_paths(),
    )
    reviewer = await suggest_reviewer(
        repo_full_name, file_names, author, github, installation_id,
    )

    # 3. Persona (cached weekly) + Triage (one LLM call).
    diff = await github.get_pr_diff(repo_full_name, pr_number, installation_id)
    # Maintainer login: in mock mode use a sane default; in production we'd
    # store this on app install. For now: repo owner as proxy.
    maintainer_login = (payload["repository"].get("owner") or {}).get("login") or "maintainer"
    persona = await extract_persona(repo_full_name, maintainer_login, github, llm, installation_id)

    analysis = await analyze_pr(
        pr_data={
            "pr_number": pr_number,
            "pr_title": pr["title"],
            "author": author,
            "files": files,
            "additions": pr["additions"],
            "deletions": pr["deletions"],
            "diff": diff,
        },
        persona=persona, trust=trust, risk=risk,
        suggested_reviewer=reviewer, llm=llm,
    )

    # 4. NemoClaw gates BEFORE any side-effect.
    triage_comment = format_triage_comment(analysis, trust, risk, reviewer)
    try:
        policy.assert_disclosure(triage_comment)
    except NemoClawViolation as e:
        log.error("NemoClaw blocked triage comment: %s", e)
        return {"ok": False, "handled_as": "blocked_by_nemoclaw", "reason": str(e)}

    # 5. Side effects.
    await github.ensure_labels_exist(repo_full_name, LABEL_COLORS, installation_id)
    labels_to_add = []
    if policy.can_apply_label(f"trust:{trust['trust_level']}"):
        labels_to_add.append(f"trust:{trust['trust_level']}")
    if policy.can_apply_label(f"risk:{risk['risk_level']}"):
        labels_to_add.append(f"risk:{risk['risk_level']}")
    if labels_to_add:
        await github.add_labels(repo_full_name, pr_number, labels_to_add, installation_id)

    head_sha = (pr.get("head") or {}).get("sha", "")
    check_run_id = await github.create_check_run(
        repo_full_name, head_sha=head_sha, installation_id=installation_id,
        title=f"PRGenie: trust={trust['trust_level']} risk={risk['risk_level']}",
        summary=format_check_run_summary(analysis, trust, risk),
        conclusion="neutral",  # never block — informational only
    )

    comment_id = None
    if policy.can_post_comment():
        comment_id = await github.post_pr_comment(repo_full_name, pr_number, triage_comment, installation_id)

    # 6. Persist for /prgenie review later.
    with get_session() as s:
        save_pr_analysis(s, pr_number, repo_full_name, {
            **analysis,
            "trust_level": trust["trust_level"],
            "risk_level": risk["risk_level"],
            "suggested_reviewer": reviewer,
            "check_run_id": check_run_id,
            "bot_comment_id": comment_id,
        })

    log.info(
        "PR pipeline ok: repo=%s pr=#%s trust=%s risk=%s priority=%s reviewer=%s",
        repo_full_name, pr_number, trust["trust_level"], risk["risk_level"],
        analysis.get("priority"), reviewer,
    )
    return {
        "ok": True,
        "handled_as": "pr_event",
        "repo": repo_full_name,
        "pr_number": pr_number,
        "action": payload.get("action"),
        "trust_level": trust["trust_level"],
        "risk_level": risk["risk_level"],
        "priority": analysis.get("priority"),
        "suggested_reviewer": reviewer,
        "labels_applied": labels_to_add,
        "check_run_id": check_run_id,
        "comment_id": comment_id,
        "should_escalate": risk["should_escalate"],
    }


async def handle_command(payload: dict) -> dict:
    body = (payload.get("comment", {}) or {}).get("body", "").strip()
    issue = payload.get("issue", {}) or {}
    repo_full_name = payload["repository"]["full_name"]
    installation_id = payload["installation"]["id"]
    pr_number = issue.get("number")
    parts = body.split()

    log.info("command: repo=%s pr=#%s body=%r", repo_full_name, pr_number, body)

    if len(parts) < 2 or parts[0] != "/prgenie":
        return {"ok": True, "handled_as": "command_unknown", "command": parts}

    sub = parts[1].lower()

    if sub == "review":
        return await _handle_review_command(payload, repo_full_name, installation_id, pr_number)

    return {"ok": True, "handled_as": "command_unknown", "command": parts}


async def _handle_review_command(payload: dict, repo_full_name: str, installation_id: int, pr_number: int) -> dict:
    """Handle `/prgenie review` — generate inline review comments via the maintainer's voice."""
    github = get_github_client()
    llm = get_llm_client()
    policy = await PolicyEnforcer.from_repo(repo_full_name, github, installation_id)

    # NemoClaw: only allowed when human-triggered.
    if not policy.can_submit_review(triggered_by_command=True):
        return {"ok": False, "handled_as": "review_blocked_by_policy"}

    # Need cached triage so the review is grounded in the same concerns.
    with get_session() as s:
        cached = get_pr_analysis(s, pr_number, repo_full_name)
        persona_row = get_persona(s, repo_full_name)

    if cached is None:
        msg = "⚠️ PRGenie has no analysis cached for this PR yet. Reopen or push a commit to trigger triage. _AI-assisted notice._"
        await github.post_pr_comment(repo_full_name, pr_number, msg, installation_id)
        return {"ok": True, "handled_as": "review_no_analysis"}

    analysis = analysis_to_dict(cached)
    persona = persona_to_dict(persona_row) if persona_row else {}
    diff = await github.get_pr_diff(repo_full_name, pr_number, installation_id)

    review = await generate_review(
        diff, persona, analysis.get("concerns", []), policy, llm,
    )

    body = (
        f"🤖 **PRGenie Review** — AI-assisted, grounded in the cached triage analysis.\n\n"
        f"{analysis.get('summary', '')}"
    )
    review_id = await github.submit_pr_review(
        repo_full_name, pr_number, installation_id,
        body=body,
        comments=review["comments"],
        event=review["verdict"],
    )

    return {
        "ok": True,
        "handled_as": "review_submitted",
        "review_id": review_id,
        "verdict": review["verdict"],
        "comment_count": len(review["comments"]),
        "dropped_count": len(review["dropped"]),
    }


async def handle_issue_event(payload: dict) -> dict:
    issue = payload["issue"]
    repo_full_name = payload["repository"]["full_name"]
    installation_id = payload["installation"]["id"]
    issue_number = issue["number"]

    github = get_github_client()
    policy = await PolicyEnforcer.from_repo(repo_full_name, github, installation_id)

    issue_data = {
        "number": issue_number,
        "title": issue.get("title", ""),
        "body": issue.get("body") or "",
        "reactions": (issue.get("reactions") or {}).get("total_count", 0),
        "comments": issue.get("comments", 0),
        "labels": [(l.get("name") if isinstance(l, dict) else l) for l in issue.get("labels", [])],
        "created_at": issue.get("created_at"),
    }

    score = await score_and_persist(repo_full_name, issue_data)

    if policy.can_apply_label(f"demand:{score['demand_level']}"):
        await github.ensure_labels_exist(repo_full_name, LABEL_COLORS, installation_id)
        await github.add_labels(repo_full_name, issue_number, [f"demand:{score['demand_level']}"], installation_id)

    posted_comment = False
    if score["reactions"] >= policy.get_demand_threshold() and score["demand_level"] == "high":
        comment = format_demand_comment(score)
        await github.post_issue_comment(repo_full_name, issue_number, comment, installation_id)
        posted_comment = True

    return {
        "ok": True,
        "handled_as": "issue_event",
        "repo": repo_full_name,
        "issue_number": issue_number,
        "action": payload.get("action"),
        "demand_level": score["demand_level"],
        "priority_score": score["priority_score"],
        "comment_posted": posted_comment,
    }


async def handle_review_ingestion(payload: dict) -> dict:
    review = payload.get("review", {}) or {}
    repo = (payload.get("repository", {}) or {}).get("full_name")
    log.info(
        "review submitted: repo=%s pr=#%s reviewer=%s state=%s",
        repo,
        (payload.get("pull_request", {}) or {}).get("number"),
        (review.get("user") or {}).get("login"),
        review.get("state"),
    )
    return {"ok": True, "handled_as": "review_ingested"}
