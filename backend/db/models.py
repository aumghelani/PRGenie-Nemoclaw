"""
SQLModel tables for PRClaw.

All cross-row relationships are tracked by (repo_full_name, ...) — we keep
each row scoped to a single repo so we can drop a repo cleanly when the app
is uninstalled. JSON-shaped fields (lists, dicts) are stored as TEXT and
serialized via the helpers in store.py.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MaintainerPersona(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    repo_full_name: str = Field(index=True)            # "owner/repo"
    maintainer_login: str
    focus: str = "[]"                                   # JSON list[str]
    strictness: float = 0.7                             # 0.0 - 1.0
    tone: str = "constructive"
    avg_comments_per_pr: float = 0.0
    common_phrases: str = "[]"                          # JSON list[str]
    tolerance: str = "{}"                               # JSON dict[str, str]
    updated_at: datetime = Field(default_factory=_utcnow)


class ContributorTrust(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    login: str = Field(index=True)
    repo_full_name: str = Field(index=True)
    trust_level: str                                    # "high" | "medium" | "new" | "flagged"
    trust_score: float                                  # 0.0 - 1.0
    signals: str = "{}"                                 # JSON dict
    updated_at: datetime = Field(default_factory=_utcnow)


class PRAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pr_number: int = Field(index=True)
    repo_full_name: str = Field(index=True)
    trust_level: str
    risk_level: str                                     # "low" | "medium" | "high" | "critical"
    priority: str                                       # "low" | "medium" | "high"
    summary: str
    concerns: str = "[]"                                # JSON list[str]
    checklist: str = "[]"                               # JSON list[str]
    suggested_reviewer: Optional[str] = None
    suggested_action: Optional[str] = None
    check_run_id: Optional[int] = None
    bot_comment_id: Optional[int] = None
    created_at: datetime = Field(default_factory=_utcnow)


class IssueScore(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    issue_number: int = Field(index=True)
    repo_full_name: str = Field(index=True)
    demand_score: float
    neglect_score: float
    priority_score: float
    demand_level: str                                   # "high" | "medium" | "low"
    cluster_id: Optional[str] = None
    reactions: int = 0
    unique_commenters: int = 0
    days_open: int = 0
    updated_at: datetime = Field(default_factory=_utcnow)
