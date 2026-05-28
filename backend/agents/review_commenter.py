"""
Review Commenter — the Senior Consultant.

Triggered ONLY by `/prclaw review` from a human. Generates inline
review comments grounded in the cached triage concerns + the maintainer
persona, and submits a formal GitHub PR review.

NemoClaw constraints applied here:
  - can_submit_review(triggered_by_command=True) MUST be True (the webhook
    handler enforces this before calling us).
  - Each generated comment is run through validate_review_comment(); rejects
    are dropped (not raised — partial review is better than no review).
  - Verdict can only be COMMENT or REQUEST_CHANGES (NEVER APPROVE — see
    SYSTEM_REVIEW prompt and tool schema).
"""
from __future__ import annotations

from typing import Any

from backend.llm import prompts
from backend.llm.client import LLMClient
from backend.nemo_claw.policy_enforcer import PolicyEnforcer

DIFF_BUDGET = 4000


def _truncate(text: str, n: int) -> str:
    return text if len(text) <= n else text[:n] + "\n... [truncated] ..."


async def generate_review(
    pr_diff: str,
    persona: dict[str, Any],
    concerns: list[str],
    policy: PolicyEnforcer,
    llm: LLMClient,
) -> dict[str, Any]:
    """
    Returns:
        {
          "comments": [{"path", "line", "body"}, ...],   # validated by NemoClaw
          "verdict": "COMMENT" | "REQUEST_CHANGES",
          "dropped": [{"reason", "comment"}],            # rejected by NemoClaw
        }
    """
    user_msg = prompts.USER_REVIEW.format(
        focus=str(persona.get("focus", [])),
        tone=persona.get("tone", "constructive"),
        common_phrases=str(persona.get("common_phrases", [])),
        concerns="\n".join(f"- {c}" for c in concerns) or "(no triage concerns recorded)",
        diff=_truncate(pr_diff, DIFF_BUDGET),
    )

    raw = await llm.complete_tool(
        system=prompts.SYSTEM_REVIEW,
        user=user_msg,
        tool=prompts.REVIEW_TOOL,
    )

    valid_comments: list[dict] = []
    dropped: list[dict] = []
    for comment in raw.get("comments", []):
        ok, reason = policy.validate_review_comment(comment.get("body", ""))
        if ok:
            valid_comments.append(comment)
        else:
            dropped.append({"reason": reason, "comment": comment})

    verdict = raw.get("verdict", "COMMENT")
    # Hard guardrail in code, even though prompt + schema also block it.
    if verdict == "APPROVE":
        verdict = "COMMENT"

    return {"comments": valid_comments, "verdict": verdict, "dropped": dropped}
