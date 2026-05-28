"""
Persona Extractor — the Patient Profiler.

One LLM call per maintainer per week. Reads the maintainer's last 50 PR
reviews, extracts focus areas, strictness, tone, common phrases, tolerance.

Caching: if a MaintainerPersona row exists and was updated within
`refresh_days` (default 7), reuse it. Otherwise refetch + recompute.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from backend.db.session import get_session
from backend.db.store import get_persona, persona_to_dict, upsert_persona
from backend.github_client import GitHubClient
from backend.llm import prompts
from backend.llm.client import LLMClient


def _format_reviews_for_prompt(reviews: list[dict], char_budget: int = 3000) -> str:
    """Pack as many reviews as fit in the budget, most recent first."""
    out: list[str] = []
    used = 0
    for r in reviews:
        chunk = (
            f"---\n"
            f"PR #{r.get('pr_number')} ({r.get('state')}):\n"
            f"{(r.get('body') or '').strip()}\n"
        )
        if used + len(chunk) > char_budget:
            break
        out.append(chunk)
        used += len(chunk)
    return "".join(out) or "(no reviews available)"


def _persona_is_fresh(updated_at: datetime, refresh_days: float) -> bool:
    return (datetime.now() - updated_at) < timedelta(days=refresh_days)


async def extract_persona(
    repo_full_name: str,
    maintainer_login: str,
    github: GitHubClient,
    llm: LLMClient,
    installation_id: int,
    *,
    refresh_days: float = 7.0,
    review_limit: int = 50,
) -> dict[str, Any]:
    """Returns the persona dict (focus, strictness, tone, common_phrases, tolerance)."""
    # 1. Cache check.
    with get_session() as s:
        cached = get_persona(s, repo_full_name)
        if cached is not None and _persona_is_fresh(cached.updated_at, refresh_days):
            d = persona_to_dict(cached)
            d["cached"] = True
            return d

    # 2. Fetch reviews.
    reviews = await github.get_maintainer_reviews(repo_full_name, maintainer_login, installation_id, limit=review_limit)
    reviews_text = _format_reviews_for_prompt(reviews)

    # 3. LLM call.
    persona = await llm.complete_tool(
        system=prompts.SYSTEM_PERSONA,
        user=prompts.USER_PERSONA.format(
            login=maintainer_login,
            review_count=len(reviews),
            reviews_text=reviews_text,
        ),
        tool=prompts.PERSONA_TOOL,
    )

    # 4. Persist.
    with get_session() as s:
        upsert_persona(s, repo_full_name, maintainer_login, persona)

    persona["maintainer_login"] = maintainer_login
    persona["cached"] = False
    return persona
