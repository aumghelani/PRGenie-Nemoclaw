"""
CRUD helpers — all functions take a Session so callers control transaction scope.

Convention:
- upsert_* :: insert or update by natural key (e.g. (repo, login))
- get_*    :: returns model | None
- list_*   :: returns list[model]

JSON fields (focus, common_phrases, signals, concerns, checklist, tolerance)
are stored as TEXT and (de)serialized at the boundary so call sites work
with native Python lists/dicts.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
from typing import Any, Iterable

from sqlmodel import Session, select

from backend.db.models import (
    ContributorTrust,
    IssueScore,
    MaintainerPersona,
    PRAnalysis,
)

# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

_JSON_FIELDS = {
    MaintainerPersona: ("focus", "common_phrases", "tolerance"),
    ContributorTrust: ("signals",),
    PRAnalysis: ("concerns", "checklist"),
}


def _dump_json(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        # Already serialized — trust it.
        return value
    return json.dumps(value, ensure_ascii=False)


def _load_json(text: str | None, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


# ---------------------------------------------------------------------------
# MaintainerPersona
# ---------------------------------------------------------------------------


def upsert_persona(
    session: Session,
    repo_full_name: str,
    maintainer_login: str,
    persona_data: dict,
) -> MaintainerPersona:
    row = session.exec(
        select(MaintainerPersona).where(
            MaintainerPersona.repo_full_name == repo_full_name,
            MaintainerPersona.maintainer_login == maintainer_login,
        )
    ).first()

    fields = {
        "maintainer_login": maintainer_login,
        "focus": _dump_json(persona_data.get("focus", [])),
        "strictness": float(persona_data.get("strictness", 0.7)),
        "tone": persona_data.get("tone", "constructive"),
        "avg_comments_per_pr": float(persona_data.get("avg_comments_per_pr", 0.0)),
        "common_phrases": _dump_json(persona_data.get("common_phrases", [])),
        "tolerance": _dump_json(persona_data.get("tolerance", {})),
        "updated_at": _utcnow(),
    }

    if row is None:
        row = MaintainerPersona(repo_full_name=repo_full_name, **fields)
        session.add(row)
    else:
        for k, v in fields.items():
            setattr(row, k, v)
    session.commit()
    session.refresh(row)
    return row


def get_persona(session: Session, repo_full_name: str) -> MaintainerPersona | None:
    return session.exec(
        select(MaintainerPersona).where(MaintainerPersona.repo_full_name == repo_full_name)
    ).first()


def persona_to_dict(p: MaintainerPersona) -> dict:
    return {
        "maintainer_login": p.maintainer_login,
        "focus": _load_json(p.focus, []),
        "strictness": p.strictness,
        "tone": p.tone,
        "avg_comments_per_pr": p.avg_comments_per_pr,
        "common_phrases": _load_json(p.common_phrases, []),
        "tolerance": _load_json(p.tolerance, {}),
        "updated_at": p.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# ContributorTrust
# ---------------------------------------------------------------------------


def upsert_trust(
    session: Session,
    login: str,
    repo_full_name: str,
    trust_data: dict,
) -> ContributorTrust:
    row = session.exec(
        select(ContributorTrust).where(
            ContributorTrust.login == login,
            ContributorTrust.repo_full_name == repo_full_name,
        )
    ).first()

    fields = {
        "trust_level": trust_data["trust_level"],
        "trust_score": float(trust_data["trust_score"]),
        "signals": _dump_json(trust_data.get("signals", {})),
        "updated_at": _utcnow(),
    }

    if row is None:
        row = ContributorTrust(login=login, repo_full_name=repo_full_name, **fields)
        session.add(row)
    else:
        for k, v in fields.items():
            setattr(row, k, v)
    session.commit()
    session.refresh(row)
    return row


def get_trust(session: Session, login: str, repo_full_name: str) -> ContributorTrust | None:
    return session.exec(
        select(ContributorTrust).where(
            ContributorTrust.login == login,
            ContributorTrust.repo_full_name == repo_full_name,
        )
    ).first()


def get_fresh_trust(
    session: Session,
    login: str,
    repo_full_name: str,
    max_age_hours: float,
) -> ContributorTrust | None:
    """Return cached trust only if updated within the freshness window."""
    row = get_trust(session, login, repo_full_name)
    if row is None:
        return None
    if _utcnow() - row.updated_at > timedelta(hours=max_age_hours):
        return None
    return row


def trust_to_dict(t: ContributorTrust) -> dict:
    return {
        "login": t.login,
        "trust_level": t.trust_level,
        "trust_score": t.trust_score,
        "signals": _load_json(t.signals, {}),
        "updated_at": t.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# PRAnalysis
# ---------------------------------------------------------------------------


def save_pr_analysis(
    session: Session,
    pr_number: int,
    repo_full_name: str,
    analysis_data: dict,
) -> PRAnalysis:
    row = session.exec(
        select(PRAnalysis).where(
            PRAnalysis.pr_number == pr_number,
            PRAnalysis.repo_full_name == repo_full_name,
        )
    ).first()

    fields = {
        "trust_level": analysis_data.get("trust_level", "new"),
        "risk_level": analysis_data.get("risk_level", "low"),
        "priority": analysis_data.get("priority", "medium"),
        "summary": analysis_data.get("summary", ""),
        "concerns": _dump_json(analysis_data.get("concerns", [])),
        "checklist": _dump_json(analysis_data.get("checklist", [])),
        "suggested_reviewer": analysis_data.get("suggested_reviewer"),
        "suggested_action": analysis_data.get("suggested_action"),
        "check_run_id": analysis_data.get("check_run_id"),
        "bot_comment_id": analysis_data.get("bot_comment_id"),
    }

    if row is None:
        row = PRAnalysis(pr_number=pr_number, repo_full_name=repo_full_name, **fields)
        session.add(row)
    else:
        for k, v in fields.items():
            setattr(row, k, v)
    session.commit()
    session.refresh(row)
    return row


def get_pr_analysis(
    session: Session,
    pr_number: int,
    repo_full_name: str,
) -> PRAnalysis | None:
    return session.exec(
        select(PRAnalysis).where(
            PRAnalysis.pr_number == pr_number,
            PRAnalysis.repo_full_name == repo_full_name,
        )
    ).first()


def analysis_to_dict(a: PRAnalysis) -> dict:
    return {
        "pr_number": a.pr_number,
        "trust_level": a.trust_level,
        "risk_level": a.risk_level,
        "priority": a.priority,
        "summary": a.summary,
        "concerns": _load_json(a.concerns, []),
        "checklist": _load_json(a.checklist, []),
        "suggested_reviewer": a.suggested_reviewer,
        "suggested_action": a.suggested_action,
        "check_run_id": a.check_run_id,
        "bot_comment_id": a.bot_comment_id,
        "created_at": a.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# IssueScore
# ---------------------------------------------------------------------------


def upsert_issue_score(
    session: Session,
    issue_number: int,
    repo_full_name: str,
    score_data: dict,
) -> IssueScore:
    row = session.exec(
        select(IssueScore).where(
            IssueScore.issue_number == issue_number,
            IssueScore.repo_full_name == repo_full_name,
        )
    ).first()

    fields = {
        "demand_score": float(score_data["demand_score"]),
        "neglect_score": float(score_data.get("neglect_score", 0.0)),
        "priority_score": float(score_data.get("priority_score", score_data["demand_score"])),
        "demand_level": score_data.get("demand_level", "low"),
        "cluster_id": score_data.get("cluster_id"),
        "reactions": int(score_data.get("reactions", 0)),
        "unique_commenters": int(score_data.get("unique_commenters", 0)),
        "days_open": int(score_data.get("days_open", 0)),
        "updated_at": _utcnow(),
    }

    if row is None:
        row = IssueScore(issue_number=issue_number, repo_full_name=repo_full_name, **fields)
        session.add(row)
    else:
        for k, v in fields.items():
            setattr(row, k, v)
    session.commit()
    session.refresh(row)
    return row


def get_high_demand_issues(
    session: Session,
    repo_full_name: str,
    threshold: float = 8.0,
) -> list[IssueScore]:
    return list(session.exec(
        select(IssueScore).where(
            IssueScore.repo_full_name == repo_full_name,
            IssueScore.priority_score >= threshold,
        ).order_by(IssueScore.priority_score.desc())
    ))


def get_unclustered_issues(
    session: Session,
    repo_full_name: str,
) -> list[IssueScore]:
    return list(session.exec(
        select(IssueScore).where(
            IssueScore.repo_full_name == repo_full_name,
            IssueScore.cluster_id.is_(None),
        )
    ))


def set_cluster_ids(session: Session, assignments: Iterable[tuple[int, str, str]]) -> int:
    """assignments: iterable of (issue_number, repo_full_name, cluster_id)."""
    updated = 0
    for issue_number, repo, cluster_id in assignments:
        row = session.exec(
            select(IssueScore).where(
                IssueScore.issue_number == issue_number,
                IssueScore.repo_full_name == repo,
            )
        ).first()
        if row is not None:
            row.cluster_id = cluster_id
            updated += 1
    session.commit()
    return updated
