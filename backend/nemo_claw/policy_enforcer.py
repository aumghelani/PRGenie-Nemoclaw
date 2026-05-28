"""
NemoClaw policy enforcer — the hospital safety officer.

Loads .github/prgenie.yml from the target repo (via GitHubClient) and
exposes guards used by every agent before any side-effect.

  policy = await PolicyEnforcer.from_repo(repo, github, install_id)
  if not policy.can_apply_label("trust:high"): return
  if policy.is_action_forbidden("merge_pr"): raise NemoClawViolation(...)

Forbidden actions in HARD_FORBIDDEN are blocked regardless of YAML.
The repo's YAML can ADD to the forbidden list but never REMOVE.
"""
from __future__ import annotations

import re
from typing import Any

import yaml

from backend.github_client import GitHubClient
from backend.nemo_claw.schemas import (
    DEFAULT_POLICY,
    HARD_FORBIDDEN,
    PolicyDoc,
)

POLICY_PATH = ".github/prgenie.yml"

# Heuristic content checks for review-comment validation.
HARSH_PATTERNS = [
    r"\bidiot\b", r"\bstupid\b", r"\bdumb\b", r"\bgarbage\b",
    r"\btrash\b", r"\bworthless\b", r"\bawful\b",
    r"this is terrible", r"what were you thinking",
]


class NemoClawViolation(Exception):
    """Raised when an agent attempts a hard-forbidden action."""


def _deep_merge(defaults: dict, override: dict) -> dict:
    """Merge override INTO defaults, recursively. override wins on scalars,
    lists in override REPLACE defaults (so escalate_on can be redefined)."""
    out = dict(defaults)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class PolicyEnforcer:
    def __init__(self, policy: dict[str, Any]):
        self.policy = policy
        # Validate via Pydantic — catches malformed YAML early.
        self.doc = PolicyDoc(**policy)
        # Merge repo forbidden list with hard-forbidden. Hard always wins.
        repo_forbidden = set(policy.get("forbidden") or [])
        self._forbidden: frozenset[str] = frozenset(repo_forbidden | set(HARD_FORBIDDEN))

    # ------------------------------------------------------------------

    @classmethod
    async def from_repo(
        cls,
        repo_full_name: str,
        github: GitHubClient,
        installation_id: int,
    ) -> "PolicyEnforcer":
        raw = await github.get_repo_file(repo_full_name, POLICY_PATH, installation_id)
        if not raw:
            return cls(DEFAULT_POLICY)
        try:
            parsed = yaml.safe_load(raw) or {}
        except yaml.YAMLError:
            # Bad YAML → safer to fall back to defaults than to crash the pipeline.
            return cls(DEFAULT_POLICY)
        merged = _deep_merge(DEFAULT_POLICY, parsed)
        return cls(merged)

    # ------------------------------------------------------------------
    # Action gates
    # ------------------------------------------------------------------

    def is_action_forbidden(self, action: str) -> bool:
        return action in self._forbidden

    def can_post_comment(self) -> bool:
        # Informational comments are always allowed; the disclosure footer
        # is what the post_without_ai_disclosure rule guards. We assume the
        # comment formatter always includes the footer (verified in tests).
        return True

    def can_apply_label(self, label: str) -> bool:
        prefix = label.split(":", 1)[0]
        if prefix == "trust" and not self.doc.trust.auto_label:
            return False
        if prefix == "risk" and not self.doc.risk.auto_label:
            return False
        if prefix == "demand" and not self.doc.demand.auto_label:
            return False
        return True

    def can_submit_review(self, *, triggered_by_command: bool) -> bool:
        # The Review Commenter ONLY runs on a human /prclaw review command.
        return bool(triggered_by_command)

    def should_escalate(self, risk_level: str, trust_level: str) -> bool:
        return risk_level in ("critical", "high") and trust_level in ("new", "flagged")

    def get_demand_threshold(self) -> int:
        return self.doc.demand.comment_threshold

    def get_cluster_min_size(self) -> int:
        return self.doc.demand.cluster_min_size

    def extra_sensitive_paths(self) -> list[str]:
        return list(self.doc.risk.escalate_on or [])

    # ------------------------------------------------------------------
    # Content gates
    # ------------------------------------------------------------------

    def validate_review_comment(self, body: str) -> tuple[bool, str]:
        """Returns (is_valid, reason_if_invalid)."""
        text = (body or "").strip()
        if not text:
            return False, "empty body"
        lowered = text.lower()
        for pattern in HARSH_PATTERNS:
            if re.search(pattern, lowered):
                return False, f"harsh language matched: {pattern!r}"
        if len(text) < 10:
            return False, "too short to be useful"
        return True, ""

    def has_ai_disclosure(self, body: str) -> bool:
        """The post_without_ai_disclosure rule requires every bot comment
        to mention it's AI-generated. PR_TRIAGE_COMMENT footer satisfies this."""
        markers = ("PRGenie", "AI-assisted", "🤖", "AI-generated")
        return any(m in body for m in markers)

    def assert_disclosure(self, body: str) -> None:
        """Raise NemoClawViolation if a comment is missing the AI disclosure."""
        if "post_without_ai_disclosure" in self._forbidden and not self.has_ai_disclosure(body):
            raise NemoClawViolation(
                "post_without_ai_disclosure: comment missing AI disclosure marker"
            )
