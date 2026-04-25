"""
Trust Scorer — the Receptionist.

Pure-rule contributor trust scoring. Zero LLM calls. Zero identity signals
(name, org, photo, nationality) — NemoClaw `use_identity_signals` is in
`forbidden`. Behavior-only.

Scoring formula (weights from CLAUDE.md):
    trust_score =
        merge_rate       * 0.40
      + response_score   * 0.30
      + resolution_rate  * 0.20
      + age_score        * 0.10

Mapping to trust_level:
    >= 0.75               → high
    >= 0.45               → medium
    total_prs == 0        → new        (overrides low score for first-time contributors)
    otherwise             → flagged

Caching: if an existing ContributorTrust row was updated within
`cache_hours` (default 24), we reuse it and skip GitHub.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.db.session import get_session
from backend.db.store import (
    get_fresh_trust,
    trust_to_dict,
    upsert_trust,
)
from backend.github_client import GitHubClient


# ---------------------------------------------------------------------------
# Pure helpers (testable without mocks)
# ---------------------------------------------------------------------------


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _compute_signals(prs: list[dict], user_created_at: str | None) -> dict[str, Any]:
    """Aggregate raw signals from the GitHub history."""
    total_prs = len(prs)
    merged_prs = sum(1 for p in prs if p.get("merged"))
    closed_no_merge = sum(1 for p in prs if p.get("state") == "closed" and not p.get("merged"))

    merge_rate = (merged_prs / total_prs) if total_prs else 0.0

    # Account age (we don't have review thread data yet → punt response/resolution to neutral defaults).
    user_dt = _parse_iso(user_created_at)
    if user_dt is not None:
        now = datetime.now(timezone.utc)
        age_days = max(0, (now - user_dt).days)
    else:
        age_days = 0

    # TODO: when github_client gains get_review_threads(), compute these for real.
    # For now, neutral defaults so account_age + merge_rate dominate.
    avg_response_hours = 24.0
    resolved_changes = 0
    total_requested_changes = 0

    return {
        "total_prs": total_prs,
        "merged_prs": merged_prs,
        "closed_without_merge": closed_no_merge,
        "merge_rate": round(merge_rate, 3),
        "account_age_days": age_days,
        "avg_response_hours": avg_response_hours,
        "resolved_changes": resolved_changes,
        "total_requested_changes": total_requested_changes,
    }


def _score_from_signals(signals: dict[str, Any]) -> tuple[float, str]:
    """Return (trust_score, trust_level) from raw signals."""
    total_prs = signals["total_prs"]
    merge_rate = signals["merge_rate"]
    age_days = signals["account_age_days"]
    avg_response_hours = signals["avg_response_hours"]
    resolved = signals["resolved_changes"]
    requested = signals["total_requested_changes"]

    # 24h response = perfect. Faster than that still 1.0.
    response_score = min(1.0, 24.0 / max(1.0, avg_response_hours))
    resolution_rate = (resolved / requested) if requested else 0.5  # neutral when no signal
    age_score = min(1.0, age_days / 365.0)

    score = (
        merge_rate * 0.40
        + response_score * 0.30
        + resolution_rate * 0.20
        + age_score * 0.10
    )
    score = round(min(1.0, max(0.0, score)), 3)

    # First-contact contributors are always "new" regardless of account age.
    # Otherwise apply the score thresholds. Low score WITH history = flagged.
    if total_prs == 0:
        level = "new"
    elif score >= 0.75:
        level = "high"
    elif score >= 0.45:
        level = "medium"
    else:
        level = "flagged"

    return score, level


# ---------------------------------------------------------------------------
# Async entry point
# ---------------------------------------------------------------------------


async def compute_trust(
    login: str,
    repo_full_name: str,
    github: GitHubClient,
    installation_id: int,
    *,
    cache_hours: float = 24.0,
    pr_history_limit: int = 20,
) -> dict[str, Any]:
    """
    Returns:
        {
            "login": str,
            "trust_level": "high" | "medium" | "new" | "flagged",
            "trust_score": float,
            "signals": {...},
            "cached": bool,
        }
    """
    # 1. Cache check.
    with get_session() as s:
        cached = get_fresh_trust(s, login, repo_full_name, max_age_hours=cache_hours)
        if cached is not None:
            d = trust_to_dict(cached)
            d["cached"] = True
            return d

    # 2. Fetch from GitHub.
    prs = await github.get_contributor_prs(repo_full_name, login, installation_id, limit=pr_history_limit)
    user = await github.get_user(login, installation_id)

    # 3. Compute.
    signals = _compute_signals(prs, user.get("created_at"))
    score, level = _score_from_signals(signals)

    # 4. Persist.
    with get_session() as s:
        upsert_trust(s, login, repo_full_name, {
            "trust_level": level,
            "trust_score": score,
            "signals": signals,
        })

    return {
        "login": login,
        "trust_level": level,
        "trust_score": score,
        "signals": signals,
        "cached": False,
    }
