"""Phase 7 — NemoClaw policy enforcer."""
from __future__ import annotations

import pytest

from backend.github_client import GitHubClient
from backend.nemo_claw.policy_enforcer import (
    NemoClawViolation,
    PolicyEnforcer,
    POLICY_PATH,
)
from backend.nemo_claw.schemas import DEFAULT_POLICY, HARD_FORBIDDEN

REPO = "acme/widgets"
INSTALL = 1


@pytest.fixture
def gh():
    return GitHubClient(mock_mode=True, app_id="0", private_key_path="/x")


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


async def test_loads_from_repo_yaml(gh):
    p = await PolicyEnforcer.from_repo(REPO, gh, INSTALL)
    # Mock yaml has strictness 0.8
    assert p.doc.persona.strictness == 0.8
    assert "auth/" in p.doc.risk.escalate_on


async def test_falls_back_to_defaults_when_yaml_missing(gh, monkeypatch):
    async def no_file(repo, path, install):
        return None
    monkeypatch.setattr(gh, "get_repo_file", no_file)
    p = await PolicyEnforcer.from_repo(REPO, gh, INSTALL)
    assert p.doc.persona.strictness == 0.7  # default


async def test_falls_back_to_defaults_on_malformed_yaml(gh, monkeypatch):
    async def bad_yaml(repo, path, install):
        return "::: not: valid: yaml ["
    monkeypatch.setattr(gh, "get_repo_file", bad_yaml)
    p = await PolicyEnforcer.from_repo(REPO, gh, INSTALL)
    assert p.doc.persona.strictness == 0.7


# ---------------------------------------------------------------------------
# Forbidden actions
# ---------------------------------------------------------------------------


def test_hard_forbidden_always_blocked():
    p = PolicyEnforcer(DEFAULT_POLICY)
    for action in HARD_FORBIDDEN:
        assert p.is_action_forbidden(action) is True


def test_repo_can_add_to_forbidden_list():
    policy = {**DEFAULT_POLICY, "forbidden": ["custom_action"]}
    p = PolicyEnforcer(policy)
    assert p.is_action_forbidden("custom_action") is True
    assert p.is_action_forbidden("merge_pr") is True  # hard still in


def test_repo_cannot_remove_hard_forbidden():
    """Even if YAML omits or contradicts a hard-forbidden action, it stays blocked."""
    policy = {**DEFAULT_POLICY, "forbidden": []}
    p = PolicyEnforcer(policy)
    for action in HARD_FORBIDDEN:
        assert p.is_action_forbidden(action) is True


# ---------------------------------------------------------------------------
# Action gates
# ---------------------------------------------------------------------------


def test_can_apply_label_respects_auto_label():
    p = PolicyEnforcer({**DEFAULT_POLICY, "trust": {"auto_label": False, "high_threshold": 0.75, "cache_hours": 24.0}})
    assert p.can_apply_label("trust:high") is False
    assert p.can_apply_label("risk:medium") is True  # risk auto_label still on


def test_can_submit_review_only_with_command():
    p = PolicyEnforcer(DEFAULT_POLICY)
    assert p.can_submit_review(triggered_by_command=False) is False
    assert p.can_submit_review(triggered_by_command=True) is True


def test_should_escalate_only_high_risk_low_trust():
    p = PolicyEnforcer(DEFAULT_POLICY)
    assert p.should_escalate("critical", "new") is True
    assert p.should_escalate("high", "flagged") is True
    assert p.should_escalate("high", "high") is False
    assert p.should_escalate("medium", "new") is False


# ---------------------------------------------------------------------------
# Content gates
# ---------------------------------------------------------------------------


def test_validate_review_comment_rejects_empty():
    p = PolicyEnforcer(DEFAULT_POLICY)
    ok, reason = p.validate_review_comment("")
    assert ok is False and "empty" in reason


def test_validate_review_comment_rejects_harsh():
    p = PolicyEnforcer(DEFAULT_POLICY)
    ok, reason = p.validate_review_comment("This is stupid code.")
    assert ok is False and "harsh" in reason


def test_validate_review_comment_accepts_constructive():
    p = PolicyEnforcer(DEFAULT_POLICY)
    ok, reason = p.validate_review_comment("Consider adding a TTL here so the cache doesn't grow unbounded.")
    assert ok is True
    assert reason == ""


def test_assert_disclosure_passes_with_marker():
    p = PolicyEnforcer(DEFAULT_POLICY)
    p.assert_disclosure("🤖 PRGenie analysis ready.")  # no raise


def test_assert_disclosure_raises_without_marker():
    p = PolicyEnforcer(DEFAULT_POLICY)
    with pytest.raises(NemoClawViolation):
        p.assert_disclosure("Looks good!")


def test_extra_sensitive_paths_pulled_from_yaml():
    policy = {**DEFAULT_POLICY, "risk": {"auto_label": True, "escalate_on": ["payments/", "billing/"]}}
    p = PolicyEnforcer(policy)
    paths = p.extra_sensitive_paths()
    assert "payments/" in paths and "billing/" in paths
