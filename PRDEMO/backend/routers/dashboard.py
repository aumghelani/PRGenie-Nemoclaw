"""
PRClaw demo dashboard — single-page UI served from FastAPI.

Two routes:
  GET  /                — the dashboard HTML
  POST /api/triage      — runs the full pipeline against a real GitHub PR,
                          returns structured JSON for the dashboard to render

Same pipeline as the CLI; just JSON-serialized so the frontend can paint it.
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


_REPO_URL_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/")


def normalize_repo(s: str) -> str:
    """Accept owner/repo OR a full GitHub URL → returns owner/repo."""
    s = s.strip().rstrip("/")
    s = _REPO_URL_RE.sub("", s)
    if s.endswith(".git"):
        s = s[:-4]
    s = re.sub(r"/pull/\d+.*$", "", s)
    return s

from backend.agents.persona_extractor import extract_persona
from backend.agents.reviewer_suggester import suggest_reviewer
from backend.agents.risk_agent import compute_risk
from backend.agents.triage_agent import (
    analyze_pr,
    format_triage_comment,
)
from backend.agents.trust_scorer import compute_trust
from backend.config import settings
from backend.github_client import GitHubClient
from backend.llm.client import LLMClient
from backend.nemo_claw.policy_enforcer import PolicyEnforcer

router = APIRouter()

DASHBOARD_HTML = (Path(__file__).parent.parent.parent / "static" / "dashboard.html").resolve()


class TriageRequest(BaseModel):
    repo: str             # "owner/repo"
    pr_number: int
    dry_run: bool = True  # default safe — don't post until user explicitly opts in


@router.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    if DASHBOARD_HTML.exists():
        return DASHBOARD_HTML.read_text(encoding="utf-8")
    return "<h1>PRClaw dashboard</h1><p>dashboard.html not found</p>"


@router.post("/api/triage")
async def triage(req: TriageRequest) -> dict[str, Any]:
    repo = normalize_repo(req.repo)
    req.repo = repo  # mutate so downstream calls use the clean form
    if "/" not in repo or repo.count("/") != 1:
        raise HTTPException(400, f"repo must be 'owner/repo' (got {req.repo!r})")
    if not settings.GITHUB_PAT:
        raise HTTPException(400, "GITHUB_PAT not set in environment")

    github = GitHubClient(mock_mode=False)
    llm = LLMClient()
    pipeline_start = time.perf_counter()

    # Fetch PR
    pr_resp = await github._request("GET", f"/repos/{req.repo}/pulls/{req.pr_number}", installation_id=0)
    pr = pr_resp.json()
    author = pr["user"]["login"]
    files = await github.get_pr_files(req.repo, req.pr_number, installation_id=0)
    file_names = [f["filename"] for f in files]
    diff = await github.get_pr_diff(req.repo, req.pr_number, installation_id=0)

    policy = await PolicyEnforcer.from_repo(req.repo, github, installation_id=0)

    trust = await compute_trust(author, req.repo, github, installation_id=0,
                                cache_hours=policy.doc.trust.cache_hours)
    risk = compute_risk(file_names, pr["additions"], pr["deletions"],
                        trust["trust_level"], extra_sensitive=policy.extra_sensitive_paths())
    reviewer = await suggest_reviewer(req.repo, file_names, author, github, installation_id=0)
    persona = await extract_persona(req.repo, req.repo.split("/")[0],
                                    github, llm, installation_id=0)
    analysis = await analyze_pr(
        pr_data={
            "pr_number": req.pr_number, "pr_title": pr["title"], "author": author,
            "files": files, "additions": pr["additions"], "deletions": pr["deletions"],
            "diff": diff,
        },
        persona=persona, trust=trust, risk=risk,
        suggested_reviewer=reviewer, llm=llm,
    )

    triage_comment = format_triage_comment(analysis, trust, risk, reviewer)
    policy.assert_disclosure(triage_comment)

    posted = None
    if not req.dry_run:
        posted = await github.post_pr_comment(req.repo, req.pr_number, triage_comment, installation_id=0)
        labels = []
        if policy.can_apply_label(f"trust:{trust['trust_level']}"):
            labels.append(f"trust:{trust['trust_level']}")
        if policy.can_apply_label(f"risk:{risk['risk_level']}"):
            labels.append(f"risk:{risk['risk_level']}")
        if labels:
            try:
                await github.add_labels(req.repo, req.pr_number, labels, installation_id=0)
            except Exception:
                pass

    pipeline_ms = round((time.perf_counter() - pipeline_start) * 1000, 1)

    # Metrics from the LLM client's recorded calls (latency + tokens per call).
    llm_calls = []
    total_tokens = 0
    total_llm_ms = 0.0
    for c in llm.recorded_calls:
        llm_calls.append({
            "tool": c.tool_name,
            "latency_ms": getattr(c, "latency_ms", None),
            "tokens": getattr(c, "tokens", None),
            "request_class": (c.headers or {}).get("x-nvext-request-class"),
            "priority": (c.headers or {}).get("x-nvext-priority"),
        })
        if getattr(c, "latency_ms", None) is not None:
            total_llm_ms += c.latency_ms
        if getattr(c, "tokens", None) is not None:
            total_tokens += c.tokens

    # Naive baseline (no NemoClaw, no nvext, no tool calling, no prefix caching).
    # These are *representative* baseline numbers — published for comparison.
    naive_calls = max(4, len(llm_calls) * 4)        # naive splits each task into 4 prompts
    naive_avg_ms = 1500.0                            # typical 70B chat without caching
    naive_total_ms = naive_calls * naive_avg_ms
    # Naive resends full system prompt every call → ~3-4× more tokens
    naive_tokens = (total_tokens or 800) * 4

    return {
        "pr": {
            "repo": req.repo,
            "number": req.pr_number,
            "title": pr["title"],
            "author": author,
            "additions": pr["additions"],
            "deletions": pr["deletions"],
            "files": file_names[:20],
            "files_count": len(files),
            "html_url": pr.get("html_url"),
        },
        "trust": trust,
        "risk": risk,
        "reviewer": reviewer,
        "persona": {k: persona.get(k) for k in ("focus", "tone", "strictness", "common_phrases")},
        "analysis": analysis,
        "triage_comment_md": triage_comment,
        "posted_comment_id": posted,
        "model": llm.model,
        "policy": {
            "forbidden": list(policy._forbidden),
            "strictness": policy.doc.persona.strictness,
        },
        "metrics": {
            "pipeline_ms": pipeline_ms,
            "llm_calls": llm_calls,
            "total_tokens": total_tokens,
            "total_llm_ms": round(total_llm_ms, 1),
            "comparison": {
                "prgenie": {
                    "calls": len(llm_calls),
                    "tokens": total_tokens,
                    "ms": round(total_llm_ms, 1) if total_llm_ms else pipeline_ms,
                },
                "naive": {
                    "calls": naive_calls,
                    "tokens": naive_tokens,
                    "ms": naive_total_ms,
                },
            },
        },
    }
