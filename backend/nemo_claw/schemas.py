"""
Pydantic schemas for the .github/prclaw.yml policy file.

The schema is intentionally permissive — every section is optional, every
field has a default. Repos without a prclaw.yml get DEFAULT_POLICY exactly
as written below. A repo's YAML is merged ON TOP of these defaults
(repo > defaults).

Forbidden actions are enforced by the PolicyEnforcer regardless of YAML —
the YAML can ADD to the forbidden list but never REMOVE from it.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PersonaSection(BaseModel):
    focus: list[str] = Field(default_factory=lambda: ["correctness", "tests"])
    strictness: float = 0.7
    tone: str = "constructive"


class TrustSection(BaseModel):
    auto_label: bool = True
    high_threshold: float = 0.75
    cache_hours: float = 24.0


class RiskSection(BaseModel):
    auto_label: bool = True
    escalate_on: list[str] = Field(default_factory=list)


class DemandSection(BaseModel):
    auto_label: bool = True
    comment_threshold: int = 25
    cluster_min_size: int = 3
    cluster_interval_minutes: int = 15


# Hard-coded forbidden actions — these CANNOT be re-enabled by any YAML.
HARD_FORBIDDEN: tuple[str, ...] = (
    "merge_pr",
    "close_pr",
    "close_issue",
    "reject_contributor",
    "post_without_ai_disclosure",
    "use_identity_signals",
)


class PolicyDoc(BaseModel):
    persona: PersonaSection = Field(default_factory=PersonaSection)
    trust: TrustSection = Field(default_factory=TrustSection)
    risk: RiskSection = Field(default_factory=RiskSection)
    demand: DemandSection = Field(default_factory=DemandSection)
    forbidden: list[str] = Field(default_factory=list)


DEFAULT_POLICY: dict[str, Any] = PolicyDoc().model_dump()
