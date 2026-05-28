"""Phase 8 — Reviewer Suggester."""
from __future__ import annotations

import pytest

from backend.agents.reviewer_suggester import rank_reviewers, suggest_reviewer
from backend.github_client import GitHubClient

REPO = "acme/widgets"
INSTALL = 1


@pytest.fixture
def gh():
    return GitHubClient(mock_mode=True, app_id="0", private_key_path="/x")


async def test_suggests_top_owner_from_mock_data(gh):
    # MOCK_FILE_COMMITS:
    #   app/users.py: jane×3, alice×1
    #   requirements.txt: jane×1, alice×1
    #   tests/test_users.py: jane×1, alice×1
    #   app/cache.py: (new file, no commits)
    files = ["app/cache.py", "app/users.py", "requirements.txt", "tests/test_users.py"]
    suggested = await suggest_reviewer(REPO, files, "octocontributor", gh, INSTALL)
    assert suggested == "maintainer-jane"


async def test_excludes_pr_author_from_candidates(gh):
    files = ["app/users.py"]
    suggested = await suggest_reviewer(REPO, files, "maintainer-jane", gh, INSTALL)
    # jane is the top owner but excluded → alice wins
    assert suggested == "alice"


async def test_returns_none_when_only_new_files(gh):
    files = ["app/cache.py"]  # no commit history in mock data
    suggested = await suggest_reviewer(REPO, files, "octocontributor", gh, INSTALL)
    assert suggested is None


async def test_rank_returns_full_ordered_list(gh):
    files = ["app/users.py", "tests/test_users.py"]
    ranked = await rank_reviewers(REPO, files, "octocontributor", gh, INSTALL)
    logins = [r[0] for r in ranked]
    assert logins[0] == "maintainer-jane"
    assert "alice" in logins
    # Scores monotonically non-increasing.
    scores = [r[1] for r in ranked]
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))


async def test_max_files_caps_api_calls(gh, monkeypatch):
    seen: list[str] = []

    async def spy(repo, path, install, limit=30):
        seen.append(path)
        return [{"author_login": "alice", "date": "2026-01-01T00:00:00Z", "message": "x"}]

    monkeypatch.setattr(gh, "get_file_commits", spy)
    files = [f"app/file{i}.py" for i in range(20)]
    await suggest_reviewer(REPO, files, "octocontributor", gh, INSTALL, max_files=5)
    assert len(seen) == 5
