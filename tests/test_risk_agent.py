"""Phase 6 — Risk Agent."""
from __future__ import annotations

from backend.agents.risk_agent import compute_risk


def test_low_risk_clean_pr():
    r = compute_risk(["docs/intro.md"], 20, 5, "high")
    assert r["risk_level"] == "low"
    assert r["sensitive_files"] == []
    assert r["should_escalate"] is False


def test_sensitive_file_bumps_risk():
    r = compute_risk(["requirements.txt", "app/main.py"], 30, 5, "medium")
    assert "requirements.txt" in r["sensitive_files"]
    # 0.4 base from sensitive → medium
    assert r["risk_level"] == "medium"


def test_large_diff_bumps_risk():
    r = compute_risk(["app/foo.py"], 800, 100, "medium")  # diff_size=900
    # +0.2 for >500
    assert r["risk_score"] >= 0.2


def test_huge_diff_compounds():
    r = compute_risk(["app/foo.py"], 1500, 200, "medium")  # >1000 → +0.4 total from size
    assert r["risk_score"] >= 0.4


def test_critical_when_flagged_user_touches_sensitive_files():
    r = compute_risk(["auth/login.py", "requirements.txt"], 50, 10, "flagged")
    # 0.4 sensitive + 0.5 flagged = 0.9 → critical
    assert r["risk_level"] == "critical"
    assert r["should_escalate"] is True


def test_high_when_new_user_touches_workflows():
    r = compute_risk([".github/workflows/ci.yml"], 100, 0, "new")
    # 0.4 sensitive + 0.3 new = 0.7 → high
    assert r["risk_level"] == "high"
    assert r["should_escalate"] is True


def test_no_escalation_for_high_trust_even_on_sensitive():
    r = compute_risk(["auth/login.py"], 1500, 100, "high")
    # 0.4 sensitive + 0.4 size = 0.8 → critical, but trust=high blocks escalation
    assert r["risk_level"] == "critical"
    assert r["should_escalate"] is False


def test_extra_sensitive_paths_from_policy():
    r = compute_risk(["src/payments/charge.py"], 50, 10, "new", extra_sensitive=["payments/"])
    assert any("payments" in f for f in r["sensitive_files"])


def test_score_clamps_at_one():
    r = compute_risk(
        ["auth/x.py", "requirements.txt", ".github/workflows/ci.yml"],
        2000, 500, "flagged",
    )
    assert r["risk_score"] <= 1.0
    assert r["risk_level"] == "critical"
