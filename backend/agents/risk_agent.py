"""
Risk Agent — the Triage Nurse.

No LLM. Pattern matching on changed file paths + diff size + trust band.

Risk score formula:
    base = 0
    + 0.4  if any sensitive file touched
    + 0.2  if diff > 500 lines
    + 0.2  if diff > 1000 lines (cumulative with above → 0.4 for big diffs)
    + 0.3  if trust_level == "new"
    + 0.5  if trust_level == "flagged"
    capped at 1.0

Mapping:
    >= 0.8  → critical
    >= 0.5  → high
    >= 0.25 → medium
    else    → low

Escalation fires only when risk_level >= "high" AND trust_level in {new, flagged}.
NemoClaw enforces this — pure diff-size rage doesn't trigger an escalation.
"""
from __future__ import annotations

from typing import Any

DEFAULT_SENSITIVE_PATHS = [
    "auth/", "authentication/", "login/", "oauth/",
    "crypto/", "encryption/", "security/",
    "requirements.txt", "package.json", "package-lock.json",
    "Pipfile", "Pipfile.lock", "go.mod", "go.sum", "Cargo.toml", "Cargo.lock",
    "Dockerfile", ".github/workflows/",
    "migrations/", "schema.sql",
]


def _matches_sensitive(file_path: str, patterns: list[str]) -> bool:
    return any(p in file_path for p in patterns)


def compute_risk(
    files_changed: list[str],
    additions: int,
    deletions: int,
    trust_level: str,
    *,
    extra_sensitive: list[str] | None = None,
) -> dict[str, Any]:
    """Synchronous, pure. Returns risk dict — no DB writes."""
    sensitive_paths = list(DEFAULT_SENSITIVE_PATHS)
    if extra_sensitive:
        sensitive_paths.extend(extra_sensitive)

    sensitive_hits = [f for f in files_changed if _matches_sensitive(f, sensitive_paths)]
    diff_size = additions + deletions

    base = 0.0
    if sensitive_hits:
        base += 0.4
    if diff_size > 500:
        base += 0.2
    if diff_size > 1000:
        base += 0.2
    if trust_level == "new":
        base += 0.3
    elif trust_level == "flagged":
        base += 0.5

    score = min(1.0, base)

    if score >= 0.8:
        level = "critical"
    elif score >= 0.5:
        level = "high"
    elif score >= 0.25:
        level = "medium"
    else:
        level = "low"

    should_escalate = level in ("critical", "high") and trust_level in ("new", "flagged")

    return {
        "risk_level": level,
        "risk_score": round(score, 3),
        "sensitive_files": sensitive_hits,
        "diff_size": diff_size,
        "should_escalate": should_escalate,
    }
