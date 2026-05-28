"""
Phase 3 tests — GitHub client.

Two layers of tests:
  1. Mock mode — exercises every public method without touching the network.
  2. JWT generation — uses a temp RSA key to confirm signing works.
"""
from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from backend.github_client import (
    DIFF_ACCEPT,
    GitHubClient,
    MOCK_OPEN_ISSUES,
    MOCK_PR_FILES,
    MOCK_PRGENIE_YML,
    RecordedCall,
)

INSTALLATION_ID = 55555555
REPO = "acme/widgets"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return GitHubClient(mock_mode=True, app_id="000000", private_key_path="/nonexistent.pem")


@pytest.fixture
def temp_pem(tmp_path):
    """Generate a real 2048-bit RSA key and write it to a temp PEM file."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path = tmp_path / "github-app.pem"
    path.write_bytes(pem)
    return path


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_jwt_generation_signs_with_real_key(temp_pem):
    c = GitHubClient(mock_mode=False, app_id="123456", private_key_path=str(temp_pem))
    token = c.generate_app_jwt()

    # Decode WITHOUT verifying signature — just confirm it parses + claims look right.
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["iss"] == "123456"
    now = int(time.time())
    assert claims["iat"] <= now
    assert claims["exp"] > now
    assert claims["exp"] - claims["iat"] <= 600  # ≤ 10 min


async def test_mock_installation_token(client: GitHubClient):
    tok = await client.get_installation_token(INSTALLATION_ID)
    assert tok == f"mock_installation_token_for_{INSTALLATION_ID}"


# ---------------------------------------------------------------------------
# Read methods (mock)
# ---------------------------------------------------------------------------


async def test_get_pr_diff_returns_canned(client: GitHubClient):
    diff = await client.get_pr_diff(REPO, 42, INSTALLATION_ID)
    assert "diff --git" in diff
    assert "redis" in diff.lower()


async def test_get_pr_files_returns_list(client: GitHubClient):
    files = await client.get_pr_files(REPO, 42, INSTALLATION_ID)
    assert len(files) == len(MOCK_PR_FILES)
    assert any(f["filename"] == "requirements.txt" for f in files)


async def test_get_contributor_prs_respects_limit(client: GitHubClient):
    prs = await client.get_contributor_prs(REPO, "octocontributor", INSTALLATION_ID, limit=2)
    assert len(prs) == 2
    assert prs[0]["number"] == 30


async def test_get_maintainer_reviews_returns_history(client: GitHubClient):
    revs = await client.get_maintainer_reviews(REPO, "maintainer-jane", INSTALLATION_ID, limit=10)
    assert len(revs) == 5
    # Must contain the strict review with "edge cases" phrasing
    assert any("edge cases" in r["body"].lower() for r in revs)


async def test_get_file_commits_for_known_file(client: GitHubClient):
    commits = await client.get_file_commits(REPO, "app/users.py", INSTALLATION_ID)
    assert len(commits) == 4
    authors = {c["author_login"] for c in commits}
    assert "maintainer-jane" in authors
    assert "alice" in authors


async def test_get_file_commits_for_new_file_empty(client: GitHubClient):
    commits = await client.get_file_commits(REPO, "app/cache.py", INSTALLATION_ID)
    assert commits == []


async def test_get_open_issues_excludes_prs(client: GitHubClient):
    issues = await client.get_open_issues(REPO, INSTALLATION_ID)
    assert len(issues) == len(MOCK_OPEN_ISSUES)
    assert all(isinstance(i["number"], int) for i in issues)


async def test_get_user_returns_account(client: GitHubClient):
    u = await client.get_user("anybody", INSTALLATION_ID)
    assert u["login"] == "anybody"
    assert "created_at" in u


async def test_get_repo_file_returns_prgenie_yml(client: GitHubClient):
    yml = await client.get_repo_file(REPO, ".github/prgenie.yml", INSTALLATION_ID)
    assert yml == MOCK_PRGENIE_YML
    assert "forbidden" in yml


async def test_get_repo_file_returns_none_for_missing(client: GitHubClient):
    out = await client.get_repo_file(REPO, "nope/missing.txt", INSTALLATION_ID)
    assert out is None


# ---------------------------------------------------------------------------
# Write methods (mock — record calls)
# ---------------------------------------------------------------------------


async def test_post_pr_comment_records(client: GitHubClient):
    cid = await client.post_pr_comment(REPO, 42, "Looks great!", INSTALLATION_ID)
    assert isinstance(cid, int) and cid > 0
    assert client.recorded_calls[-1] == RecordedCall(
        method="post_pr_comment", repo=REPO, target=42, payload={"body": "Looks great!"}
    )


async def test_create_check_run_records(client: GitHubClient):
    rid = await client.create_check_run(
        REPO, head_sha="abc", installation_id=INSTALLATION_ID,
        title="PRClaw: Trust HIGH", summary="ok", conclusion="success",
    )
    assert rid > 0
    last = client.recorded_calls[-1]
    assert last.method == "create_check_run"
    assert last.payload["conclusion"] == "success"
    assert last.payload["output"]["title"] == "PRClaw: Trust HIGH"


async def test_submit_pr_review_records(client: GitHubClient):
    comments = [{"path": "app/cache.py", "line": 5, "body": "What if Redis is down?"}]
    rid = await client.submit_pr_review(
        REPO, 42, INSTALLATION_ID,
        body="AI-assisted review.",
        comments=comments,
        event="REQUEST_CHANGES",
    )
    assert rid > 0
    last = client.recorded_calls[-1]
    assert last.method == "submit_pr_review"
    assert last.payload["event"] == "REQUEST_CHANGES"
    assert last.payload["comments"] == comments


async def test_add_labels_records(client: GitHubClient):
    await client.add_labels(REPO, 42, ["trust:medium", "risk:high"], INSTALLATION_ID)
    last = client.recorded_calls[-1]
    assert last.method == "add_labels"
    assert last.payload["labels"] == ["trust:medium", "risk:high"]


async def test_ensure_labels_exist_records(client: GitHubClient):
    await client.ensure_labels_exist(REPO, {"trust:high": "2ecc71", "risk:critical": "8e44ad"}, INSTALLATION_ID)
    last = client.recorded_calls[-1]
    assert last.method == "ensure_labels_exist"
    assert "trust:high" in last.payload["labels"]


async def test_post_issue_comment_records(client: GitHubClient):
    cid = await client.post_issue_comment(REPO, 88, "High demand!", INSTALLATION_ID)
    assert cid > 0
    last = client.recorded_calls[-1]
    assert last.method == "post_issue_comment"
    assert last.target == 88


async def test_recorded_calls_accumulate(client: GitHubClient):
    await client.add_labels(REPO, 1, ["a"], INSTALLATION_ID)
    await client.add_labels(REPO, 2, ["b"], INSTALLATION_ID)
    await client.post_pr_comment(REPO, 3, "x", INSTALLATION_ID)
    assert len(client.recorded_calls) == 3
    assert [c.target for c in client.recorded_calls] == [1, 2, 3]


def test_diff_accept_header_constant():
    # Sanity: don't accidentally break the diff content-type
    assert DIFF_ACCEPT == "application/vnd.github.v3.diff"
