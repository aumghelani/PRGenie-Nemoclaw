"""
Triage Agent — the Lead Doctor.

One LLM call per PR. Combines maintainer persona + trust + risk + diff
into a structured analysis (summary, priority, concerns, checklist,
suggested_action).

Also exposes format_triage_comment() and format_check_run_summary() —
the markdown the GitHub client posts.
"""
from __future__ import annotations

from typing import Any

from backend.llm import prompts
from backend.llm.client import LLMClient

DIFF_HEAD_CHARS = 1500
DIFF_TAIL_CHARS = 1500
DIFF_TRUNCATION_MARKER = "\n\n... [diff truncated for token budget] ...\n\n"


def _truncate_diff(diff: str) -> str:
    if len(diff) <= DIFF_HEAD_CHARS + DIFF_TAIL_CHARS:
        return diff
    return diff[:DIFF_HEAD_CHARS] + DIFF_TRUNCATION_MARKER + diff[-DIFF_TAIL_CHARS:]


async def analyze_pr(
    pr_data: dict[str, Any],
    persona: dict[str, Any],
    trust: dict[str, Any],
    risk: dict[str, Any],
    suggested_reviewer: str | None,
    llm: LLMClient,
) -> dict[str, Any]:
    """
    pr_data must contain: pr_number, pr_title, author, files (list of {filename}),
                          additions, deletions, diff.
    Returns the structured triage dict (summary, priority, concerns, checklist, suggested_action).
    """
    files = pr_data["files"]
    files_list = ", ".join(f["filename"] for f in files[:20])
    if len(files) > 20:
        files_list += f", ... (+{len(files) - 20} more)"

    user_msg = prompts.USER_TRIAGE.format(
        focus=str(persona.get("focus", [])),
        tone=persona.get("tone", "constructive"),
        strictness=float(persona.get("strictness", 0.7)),
        common_phrases=str(persona.get("common_phrases", [])),
        trust_level=trust["trust_level"],
        trust_score=float(trust["trust_score"]),
        trust_signals=str(trust.get("signals", {})),
        risk_level=risk["risk_level"],
        risk_score=float(risk["risk_score"]),
        sensitive_files=str(risk.get("sensitive_files", [])),
        suggested_reviewer=f"@{suggested_reviewer}" if suggested_reviewer else "(no clear owner)",
        pr_number=pr_data["pr_number"],
        pr_title=pr_data["pr_title"],
        author=pr_data["author"],
        files_count=len(files),
        files_list=files_list,
        additions=pr_data["additions"],
        deletions=pr_data["deletions"],
        diff=_truncate_diff(pr_data["diff"]),
    )

    return await llm.complete_tool(
        system=prompts.SYSTEM_TRIAGE,
        user=user_msg,
        tool=prompts.TRIAGE_TOOL,
    )


# ---------------------------------------------------------------------------
# Comment formatting
# ---------------------------------------------------------------------------

TRUST_EMOJI = {"high": "🟢", "medium": "🟡", "new": "⚪", "flagged": "🔴"}
RISK_EMOJI = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🚨"}

PR_TRIAGE_COMMENT = """## 🤖 PRGenie Analysis

|  |  |
|---|---|
| **Contributor Trust** | {trust_emoji} `{trust_level}` (score `{trust_score:.2f}`) |
| **Risk Level** | {risk_emoji} `{risk_level}` |
| **Priority** | `{priority}` |
| **Suggested Reviewer** | {reviewer_mention} |

**Summary**
{summary}

**Concerns**
{concern_items}

**Review Checklist**
{checklist_items}

---
*Type `/prgenie review` to post inline review comments in this maintainer's voice.*
*AI-assisted analysis · Powered by [PRGenie](https://github.com/prclaw) · Policy: `.github/prgenie.yml`*
"""


def _bullets(items: list[str]) -> str:
    if not items:
        return "_(none)_"
    return "\n".join(f"- {item}" for item in items)


def format_triage_comment(
    analysis: dict[str, Any],
    trust: dict[str, Any],
    risk: dict[str, Any],
    suggested_reviewer: str | None,
) -> str:
    return PR_TRIAGE_COMMENT.format(
        trust_emoji=TRUST_EMOJI.get(trust["trust_level"], "⚪"),
        trust_level=trust["trust_level"],
        trust_score=float(trust["trust_score"]),
        risk_emoji=RISK_EMOJI.get(risk["risk_level"], "⚪"),
        risk_level=risk["risk_level"],
        priority=analysis.get("priority", "medium"),
        reviewer_mention=f"@{suggested_reviewer}" if suggested_reviewer else "_(no clear owner)_",
        summary=analysis.get("summary", "_(no summary)_"),
        concern_items=_bullets(analysis.get("concerns", [])),
        checklist_items=_bullets(analysis.get("checklist", [])),
    )


def format_check_run_summary(
    analysis: dict[str, Any],
    trust: dict[str, Any],
    risk: dict[str, Any],
) -> str:
    return (
        f"**Trust:** `{trust['trust_level']}` ({trust['trust_score']:.2f}) · "
        f"**Risk:** `{risk['risk_level']}` ({risk['risk_score']:.2f}) · "
        f"**Priority:** `{analysis.get('priority', 'medium')}`\n\n"
        f"{analysis.get('summary', '')}\n\n"
        f"**Concerns:**\n{_bullets(analysis.get('concerns', []))}"
    )
