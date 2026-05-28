"""
Reviewer Suggester — the Specialist Referrer.

No LLM. Pure git-blame ownership math via the GitHub commits API.

For each changed file (capped to first N to bound API cost):
  - fetch last 30 commits on that file
  - for each commit, ownership_score[author] += 1 / total_commits_on_file

Sum across all changed files, drop the PR author, return the top login.
Returns None if no clear owner exists (e.g. all-new files).
"""
from __future__ import annotations

from collections import defaultdict

from backend.github_client import GitHubClient


async def suggest_reviewer(
    repo_full_name: str,
    files_changed: list[str],
    pr_author: str,
    github: GitHubClient,
    installation_id: int,
    *,
    max_files: int = 10,
    commits_per_file: int = 30,
) -> str | None:
    ownership: dict[str, float] = defaultdict(float)

    for path in files_changed[:max_files]:
        commits = await github.get_file_commits(repo_full_name, path, installation_id, limit=commits_per_file)
        total = len(commits)
        if total == 0:
            continue  # new file, no history
        for c in commits:
            login = c.get("author_login")
            if not login:
                continue
            ownership[login] += 1.0 / total

    ownership.pop(pr_author, None)
    if not ownership:
        return None
    return max(ownership.items(), key=lambda kv: kv[1])[0]


async def rank_reviewers(
    repo_full_name: str,
    files_changed: list[str],
    pr_author: str,
    github: GitHubClient,
    installation_id: int,
    *,
    max_files: int = 10,
    commits_per_file: int = 30,
) -> list[tuple[str, float]]:
    """Same as suggest_reviewer but returns the full ranked list."""
    ownership: dict[str, float] = defaultdict(float)
    for path in files_changed[:max_files]:
        commits = await github.get_file_commits(repo_full_name, path, installation_id, limit=commits_per_file)
        total = len(commits)
        if total == 0:
            continue
        for c in commits:
            login = c.get("author_login")
            if not login:
                continue
            ownership[login] += 1.0 / total
    ownership.pop(pr_author, None)
    return sorted(ownership.items(), key=lambda kv: kv[1], reverse=True)
