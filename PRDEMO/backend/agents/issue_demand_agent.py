"""
Issue Demand Agent — the Public Health Officer.

Two responsibilities:

  1. score_issue(issue) — pure rule scoring per issue. No LLM. Returns
     a demand_score, neglect_score, priority_score, and a demand_level
     in {low, medium, high}.

  2. cluster_issues(repo) — batched every 15 min by main.py lifespan.
     Pulls all unclustered issues from the DB, packs them into one LLM
     call, parses the cluster assignments, writes them back.

Trust-neutral: scoring DOES NOT look at who filed the issue. NemoClaw
forbids identity signals here too.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.db.session import get_session
from backend.db.store import (
    get_unclustered_issues,
    set_cluster_ids,
    upsert_issue_score,
)
from backend.llm import prompts
from backend.llm.client import LLMClient


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def score_issue(
    issue: dict[str, Any],
    *,
    last_maintainer_response_at: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """
    issue must contain: number, title, body, reactions (int),
                        comments (int), labels (list[str]), created_at (iso).
    """
    now = now or datetime.now(timezone.utc)
    reactions = int(issue.get("reactions", 0))
    unique_commenters = int(issue.get("comments", 0))  # proxy: real version dedupes commenter logins
    created = _parse_iso(issue.get("created_at"))
    days_open = max(0, (now - created).days) if created else 0

    if last_maintainer_response_at:
        last = _parse_iso(last_maintainer_response_at)
        days_since_response = max(0, (now - last).days) if last else days_open
    else:
        days_since_response = days_open

    labels = [(l.lower() if isinstance(l, str) else "") for l in issue.get("labels", [])]
    label_weight = 1.0
    if "security" in labels:
        label_weight = 1.5
    elif "bug" in labels:
        label_weight = 1.3

    demand_score = (
        reactions * 0.4
        + unique_commenters * 0.3
        + min(days_open / 30.0, 1.0) * 0.2
        + label_weight * 0.1
    )
    neglect_score = days_since_response / 7.0
    priority_score = demand_score * max(1.0, neglect_score)

    if priority_score >= 8.0:
        demand_level = "high"
    elif priority_score >= 3.0:
        demand_level = "medium"
    else:
        demand_level = "low"

    return {
        "demand_score": round(demand_score, 3),
        "neglect_score": round(neglect_score, 3),
        "priority_score": round(priority_score, 3),
        "demand_level": demand_level,
        "reactions": reactions,
        "unique_commenters": unique_commenters,
        "days_open": days_open,
    }


# ---------------------------------------------------------------------------
# Persistence + clustering
# ---------------------------------------------------------------------------


async def score_and_persist(repo_full_name: str, issue: dict[str, Any]) -> dict[str, Any]:
    score = score_issue(issue)
    with get_session() as s:
        upsert_issue_score(s, issue["number"], repo_full_name, score)
    return score


async def cluster_issues(
    repo_full_name: str,
    issues_by_number: dict[int, dict[str, Any]],
    llm: LLMClient,
    *,
    min_cluster_size: int = 3,
) -> list[dict]:
    """
    issues_by_number maps issue_number → {title, body}. Returns the parsed
    clusters list. Also writes cluster_id back via set_cluster_ids().
    """
    with get_session() as s:
        unclustered = get_unclustered_issues(s, repo_full_name)

    target = [i for i in unclustered if i.issue_number in issues_by_number]
    if len(target) < min_cluster_size:
        return []

    issues_text = "\n".join(
        f"#{i.issue_number}: {issues_by_number[i.issue_number]['title']} — "
        f"{(issues_by_number[i.issue_number].get('body') or '')[:200]}"
        for i in target
    )

    out = await llm.complete_tool(
        system=prompts.SYSTEM_CLUSTER,
        user=prompts.USER_CLUSTER.format(issues_text=issues_text, min_size=min_cluster_size),
        tool=prompts.CLUSTER_TOOL,
    )

    clusters = out.get("clusters", [])
    assignments: list[tuple[int, str, str]] = []
    for cluster in clusters:
        cid = cluster["id"]
        for n in cluster.get("issue_numbers", []):
            assignments.append((int(n), repo_full_name, cid))

    if assignments:
        with get_session() as s:
            set_cluster_ids(s, assignments)

    return clusters


# ---------------------------------------------------------------------------
# Comment formatting
# ---------------------------------------------------------------------------

ISSUE_DEMAND_COMMENT = """## 📊 PRGenie Demand Signal

This issue has **{reactions} reactions** and **{unique_commenters} unique commenters**, open for **{days_open} days**.{maintainer_silence}

{cluster_section}

---
*Auto-surfaced by PRGenie · Label: `demand:{demand_level}` · AI-assisted*
"""


def format_demand_comment(score: dict[str, Any], cluster: dict | None = None) -> str:
    silence = ""
    if score.get("neglect_score", 0) > 1.0:
        silence = f"\n_No maintainer response in **{int(score['neglect_score'] * 7)}** days._"
    cluster_section = ""
    if cluster:
        members = ", ".join(f"#{n}" for n in cluster["issue_numbers"])
        cluster_section = (
            f"### 🧩 Cluster: {cluster['name']}\n"
            f"Related issues: {members}\n\n"
            f"{cluster['summary']}"
        )
    return ISSUE_DEMAND_COMMENT.format(
        reactions=score["reactions"],
        unique_commenters=score["unique_commenters"],
        days_open=score["days_open"],
        maintainer_silence=silence,
        demand_level=score["demand_level"],
        cluster_section=cluster_section,
    )
