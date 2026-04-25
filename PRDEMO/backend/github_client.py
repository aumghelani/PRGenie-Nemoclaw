"""
GitHub REST client for PRGenie.

Two modes, controlled by MOCK_MODE in settings (or the `mock_mode` constructor arg):

  * MOCK_MODE = True   → No network. Read methods return canned data from
                          MOCK_DATA below; write methods append to
                          self.recorded_calls and return fake IDs.
                          Used for tests + the "demo without GPU/GitHub" path.

  * MOCK_MODE = False  → Real httpx calls to api.github.com, signed with a
                          GitHub App JWT exchanged for installation tokens.
                          Tokens cached per installation_id with expiry.

All async. All methods accept installation_id so calls are scoped to the
correct repo install.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
import jwt
from cryptography.hazmat.primitives import serialization

from backend.config import settings

log = logging.getLogger("prclaw.github")

GITHUB_API = "https://api.github.com"
ACCEPT = "application/vnd.github+json"
DIFF_ACCEPT = "application/vnd.github.v3.diff"


# ---------------------------------------------------------------------------
# Mock data — used in MOCK_MODE for read methods.
# Write methods don't need canned data; they record into self.recorded_calls.
# ---------------------------------------------------------------------------

MOCK_PR_DIFF = """diff --git a/app/cache.py b/app/cache.py
new file mode 100644
index 0000000..deadbef
--- /dev/null
+++ b/app/cache.py
@@ -0,0 +1,30 @@
+import redis
+
+r = redis.Redis(host="localhost", port=6379, db=0)
+
+def get_user(user_id: int) -> dict | None:
+    cached = r.get(f"user:{user_id}")
+    if cached:
+        return json.loads(cached)
+    user = db.fetch_user(user_id)
+    r.set(f"user:{user_id}", json.dumps(user))
+    return user
"""

MOCK_PR_FILES = [
    {"filename": "app/cache.py", "status": "added", "additions": 30, "deletions": 0, "changes": 30},
    {"filename": "app/users.py", "status": "modified", "additions": 8, "deletions": 4, "changes": 12},
    {"filename": "requirements.txt", "status": "modified", "additions": 1, "deletions": 0, "changes": 1},
    {"filename": "tests/test_users.py", "status": "modified", "additions": 12, "deletions": 0, "changes": 12},
]

MOCK_CONTRIBUTOR_PRS = [
    {"number": 30, "state": "closed", "merged": True, "created_at": "2026-03-01T10:00:00Z", "merged_at": "2026-03-02T15:00:00Z"},
    {"number": 35, "state": "closed", "merged": True, "created_at": "2026-03-15T10:00:00Z", "merged_at": "2026-03-16T11:00:00Z"},
    {"number": 38, "state": "closed", "merged": False, "created_at": "2026-04-01T10:00:00Z", "merged_at": None},
    {"number": 42, "state": "open", "merged": False, "created_at": "2026-04-25T10:00:00Z", "merged_at": None},
]

MOCK_MAINTAINER_REVIEWS = [
    {"pr_number": 28, "state": "CHANGES_REQUESTED", "body": "Needs more test coverage on edge cases.", "submitted_at": "2026-03-05T12:00:00Z"},
    {"pr_number": 30, "state": "APPROVED", "body": "Looks good — ship it.", "submitted_at": "2026-03-02T14:30:00Z"},
    {"pr_number": 33, "state": "CHANGES_REQUESTED", "body": "What happens if Redis is down? We need fallback.", "submitted_at": "2026-03-12T09:15:00Z"},
    {"pr_number": 35, "state": "APPROVED", "body": "Nice, tests are thorough.", "submitted_at": "2026-03-16T10:30:00Z"},
    {"pr_number": 37, "state": "COMMENTED", "body": "Add a docstring here.", "submitted_at": "2026-03-20T14:00:00Z"},
]

MOCK_FILE_COMMITS = {
    # filename → list[commit dict]
    "app/cache.py": [],   # new file
    "app/users.py": [
        {"author_login": "maintainer-jane", "date": "2026-02-01T10:00:00Z", "message": "Initial users module"},
        {"author_login": "maintainer-jane", "date": "2026-03-01T10:00:00Z", "message": "Refactor users"},
        {"author_login": "alice", "date": "2026-03-15T10:00:00Z", "message": "Add /users/me endpoint"},
        {"author_login": "maintainer-jane", "date": "2026-04-01T10:00:00Z", "message": "Cleanup"},
    ],
    "requirements.txt": [
        {"author_login": "maintainer-jane", "date": "2026-01-15T10:00:00Z", "message": "Initial deps"},
        {"author_login": "alice", "date": "2026-03-01T10:00:00Z", "message": "Bump fastapi"},
    ],
    "tests/test_users.py": [
        {"author_login": "maintainer-jane", "date": "2026-02-01T10:00:00Z", "message": "Add user tests"},
        {"author_login": "alice", "date": "2026-03-15T10:00:00Z", "message": "Cover /users/me"},
    ],
}

MOCK_OPEN_ISSUES = [
    {"number": 88, "title": "Login fails for emails with '+' character", "body": "500s on a+b@example.com", "reactions": 12, "comments": 3, "labels": ["bug"], "created_at": "2026-04-20T10:00:00Z"},
    {"number": 91, "title": "Redis cache eviction missing", "body": "No TTL on cached user lookups", "reactions": 8, "comments": 2, "labels": ["enhancement"], "created_at": "2026-04-22T10:00:00Z"},
    {"number": 95, "title": "Login flow breaks with special chars", "body": "Same as 88 but for unicode", "reactions": 4, "comments": 1, "labels": ["bug"], "created_at": "2026-04-23T10:00:00Z"},
]

MOCK_USER = {
    "login": "octocontributor",
    "id": 9001,
    "type": "User",
    "created_at": "2025-09-01T10:00:00Z",  # ~7 months old by hackathon date
}

MOCK_PRGENIE_YML = """\
persona:
  focus: [correctness, tests, error_handling]
  strictness: 0.8
  tone: constructive but direct
trust:
  auto_label: true
  high_threshold: 0.75
  cache_hours: 24
risk:
  auto_label: true
  escalate_on:
    - auth/
    - crypto/
    - requirements.txt
    - .github/workflows/
demand:
  auto_label: true
  comment_threshold: 25
  cluster_min_size: 3
forbidden:
  - merge_pr
  - close_pr
  - close_issue
"""


# ---------------------------------------------------------------------------
# Token cache
# ---------------------------------------------------------------------------


@dataclass
class _CachedToken:
    token: str
    expires_at: float  # epoch seconds


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


@dataclass
class RecordedCall:
    """Captured side-effect from MOCK_MODE write methods. Tests assert on this."""
    method: str
    repo: str
    target: int | str | None
    payload: dict | None = None


class GitHubClient:
    def __init__(
        self,
        app_id: str | None = None,
        private_key_path: str | None = None,
        mock_mode: bool | None = None,
    ):
        self.app_id = app_id if app_id is not None else settings.GITHUB_APP_ID
        self.private_key_path = private_key_path if private_key_path is not None else settings.GITHUB_PRIVATE_KEY_PATH
        if mock_mode is None:
            mock_mode = settings.GITHUB_MOCK_MODE if settings.GITHUB_MOCK_MODE is not None else settings.MOCK_MODE
        self.mock_mode = mock_mode
        self._token_cache: dict[int, _CachedToken] = {}
        self._private_key = None  # lazy-loaded
        self.recorded_calls: list[RecordedCall] = []
        self._next_fake_id = 1_000_000  # for mock-mode write returns

    # -- auth -----------------------------------------------------------

    def _load_private_key(self):
        if self._private_key is not None:
            return self._private_key
        with open(self.private_key_path, "rb") as f:
            self._private_key = serialization.load_pem_private_key(f.read(), password=None)
        return self._private_key

    def generate_app_jwt(self) -> str:
        """JWT for the GitHub App itself (not an installation). Valid 9 min."""
        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 540, "iss": self.app_id}
        return jwt.encode(payload, self._load_private_key(), algorithm="RS256")

    async def get_installation_token(self, installation_id: int) -> str:
        if self.mock_mode:
            return f"mock_installation_token_for_{installation_id}"

        # PAT path — no JWT, no installation token, just use the PAT directly.
        if settings.GITHUB_PAT:
            return settings.GITHUB_PAT

        cached = self._token_cache.get(installation_id)
        # Refresh 60s before expiry to be safe.
        if cached and cached.expires_at > time.time() + 60:
            return cached.token

        app_jwt = self.generate_app_jwt()
        async with httpx.AsyncClient(timeout=10.0) as http:
            r = await http.post(
                f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
                headers={"Authorization": f"Bearer {app_jwt}", "Accept": ACCEPT},
            )
            r.raise_for_status()
            data = r.json()

        # GitHub returns 'expires_at' as ISO8601.
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")).timestamp()
        self._token_cache[installation_id] = _CachedToken(token=data["token"], expires_at=expires_at)
        return data["token"]

    async def _request(
        self,
        method: str,
        path: str,
        installation_id: int,
        *,
        accept: str = ACCEPT,
        params: dict | None = None,
        json: Any = None,
    ) -> httpx.Response:
        token = await self.get_installation_token(installation_id)
        headers = {
            "Authorization": f"token {token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        url = path if path.startswith("http") else f"{GITHUB_API}{path}"
        async with httpx.AsyncClient(timeout=15.0) as http:
            r = await http.request(method, url, headers=headers, params=params, json=json)
            r.raise_for_status()
            return r

    def _fake_id(self) -> int:
        self._next_fake_id += 1
        return self._next_fake_id

    def _record(self, method: str, repo: str, target, payload=None) -> int:
        call = RecordedCall(method=method, repo=repo, target=target, payload=payload)
        self.recorded_calls.append(call)
        log.info("[mock] %s repo=%s target=%s", method, repo, target)
        return self._fake_id()

    # ------------------------------------------------------------------
    # PR — read methods
    # ------------------------------------------------------------------

    async def get_pr_diff(self, repo_full_name: str, pr_number: int, installation_id: int) -> str:
        if self.mock_mode:
            return MOCK_PR_DIFF
        r = await self._request("GET", f"/repos/{repo_full_name}/pulls/{pr_number}", installation_id, accept=DIFF_ACCEPT)
        return r.text

    async def get_pr_files(self, repo_full_name: str, pr_number: int, installation_id: int) -> list[dict]:
        if self.mock_mode:
            return list(MOCK_PR_FILES)
        r = await self._request("GET", f"/repos/{repo_full_name}/pulls/{pr_number}/files", installation_id, params={"per_page": 100})
        return r.json()

    # ------------------------------------------------------------------
    # PR — write methods
    # ------------------------------------------------------------------

    async def post_pr_comment(self, repo_full_name: str, pr_number: int, body: str, installation_id: int) -> int:
        if self.mock_mode:
            return self._record("post_pr_comment", repo_full_name, pr_number, {"body": body})
        # PR conversation comments use the *issues* comments endpoint.
        r = await self._request("POST", f"/repos/{repo_full_name}/issues/{pr_number}/comments", installation_id, json={"body": body})
        return r.json()["id"]

    async def create_check_run(
        self,
        repo_full_name: str,
        head_sha: str,
        installation_id: int,
        *,
        name: str = "PRGenie",
        title: str,
        summary: str,
        conclusion: str = "neutral",  # success | failure | neutral | cancelled | skipped | timed_out | action_required
    ) -> int:
        payload = {
            "name": name,
            "head_sha": head_sha,
            "status": "completed",
            "conclusion": conclusion,
            "output": {"title": title, "summary": summary},
        }
        if self.mock_mode:
            return self._record("create_check_run", repo_full_name, head_sha, payload)
        r = await self._request("POST", f"/repos/{repo_full_name}/check-runs", installation_id, json=payload)
        return r.json()["id"]

    async def submit_pr_review(
        self,
        repo_full_name: str,
        pr_number: int,
        installation_id: int,
        *,
        body: str,
        comments: list[dict],   # [{"path","line","body"}]
        event: str = "COMMENT", # COMMENT | REQUEST_CHANGES | APPROVE
    ) -> int:
        payload = {"body": body, "event": event, "comments": comments}
        if self.mock_mode:
            return self._record("submit_pr_review", repo_full_name, pr_number, payload)
        r = await self._request("POST", f"/repos/{repo_full_name}/pulls/{pr_number}/reviews", installation_id, json=payload)
        return r.json()["id"]

    async def add_labels(self, repo_full_name: str, issue_or_pr_number: int, labels: list[str], installation_id: int) -> None:
        if self.mock_mode:
            self._record("add_labels", repo_full_name, issue_or_pr_number, {"labels": labels})
            return
        await self._request("POST", f"/repos/{repo_full_name}/issues/{issue_or_pr_number}/labels", installation_id, json={"labels": labels})

    async def ensure_labels_exist(self, repo_full_name: str, label_colors: dict[str, str], installation_id: int) -> None:
        """Create labels if missing. label_colors: {"trust:high": "2ecc71", ...}"""
        if self.mock_mode:
            self._record("ensure_labels_exist", repo_full_name, None, {"labels": label_colors})
            return
        for name, color in label_colors.items():
            try:
                await self._request(
                    "POST",
                    f"/repos/{repo_full_name}/labels",
                    installation_id,
                    json={"name": name, "color": color},
                )
            except httpx.HTTPStatusError as e:
                # 422 = already exists, fine.
                if e.response.status_code != 422:
                    raise

    # ------------------------------------------------------------------
    # Issue — write methods
    # ------------------------------------------------------------------

    async def post_issue_comment(self, repo_full_name: str, issue_number: int, body: str, installation_id: int) -> int:
        if self.mock_mode:
            return self._record("post_issue_comment", repo_full_name, issue_number, {"body": body})
        r = await self._request("POST", f"/repos/{repo_full_name}/issues/{issue_number}/comments", installation_id, json={"body": body})
        return r.json()["id"]

    # ------------------------------------------------------------------
    # Data fetching for agents
    # ------------------------------------------------------------------

    async def get_contributor_prs(self, repo_full_name: str, login: str, installation_id: int, limit: int = 20) -> list[dict]:
        if self.mock_mode:
            return list(MOCK_CONTRIBUTOR_PRS)[:limit]
        # Use search API for filtering by author + repo cleanly.
        params = {"q": f"repo:{repo_full_name} type:pr author:{login}", "per_page": limit, "sort": "created", "order": "desc"}
        r = await self._request("GET", "/search/issues", installation_id, params=params)
        items = r.json().get("items", [])
        return [
            {
                "number": it["number"],
                "state": it["state"],
                "merged": it.get("pull_request", {}).get("merged_at") is not None,
                "created_at": it["created_at"],
                "merged_at": it.get("pull_request", {}).get("merged_at"),
            }
            for it in items
        ]

    async def get_maintainer_reviews(self, repo_full_name: str, login: str, installation_id: int, limit: int = 50) -> list[dict]:
        if self.mock_mode:
            return list(MOCK_MAINTAINER_REVIEWS)[:limit]
        # No direct "all reviews by user" endpoint. We'd iterate PRs the user reviewed.
        # For now, walk the most recent N PRs and collect reviews by `login`.
        params = {"state": "all", "per_page": min(limit, 50), "sort": "updated", "direction": "desc"}
        r = await self._request("GET", f"/repos/{repo_full_name}/pulls", installation_id, params=params)
        prs = r.json()
        reviews: list[dict] = []
        for pr in prs:
            rr = await self._request("GET", f"/repos/{repo_full_name}/pulls/{pr['number']}/reviews", installation_id)
            for review in rr.json():
                if review.get("user", {}).get("login") == login and review.get("body"):
                    reviews.append({
                        "pr_number": pr["number"],
                        "state": review["state"],
                        "body": review["body"],
                        "submitted_at": review.get("submitted_at"),
                    })
                    if len(reviews) >= limit:
                        return reviews
        return reviews

    async def get_file_commits(self, repo_full_name: str, file_path: str, installation_id: int, limit: int = 50) -> list[dict]:
        if self.mock_mode:
            return list(MOCK_FILE_COMMITS.get(file_path, []))[:limit]
        params = {"path": file_path, "per_page": limit}
        r = await self._request("GET", f"/repos/{repo_full_name}/commits", installation_id, params=params)
        return [
            {
                "author_login": (c.get("author") or {}).get("login"),
                "date": c["commit"]["author"]["date"],
                "message": c["commit"]["message"],
            }
            for c in r.json()
            if (c.get("author") or {}).get("login")
        ]

    async def get_open_issues(self, repo_full_name: str, installation_id: int, limit: int = 50) -> list[dict]:
        if self.mock_mode:
            return list(MOCK_OPEN_ISSUES)[:limit]
        params = {"state": "open", "per_page": limit, "sort": "updated", "direction": "desc"}
        r = await self._request("GET", f"/repos/{repo_full_name}/issues", installation_id, params=params)
        # Filter out PRs (GitHub treats PRs as issues in this endpoint).
        return [
            {
                "number": it["number"],
                "title": it["title"],
                "body": it.get("body") or "",
                "reactions": it.get("reactions", {}).get("total_count", 0),
                "comments": it.get("comments", 0),
                "labels": [l["name"] for l in it.get("labels", [])],
                "created_at": it["created_at"],
            }
            for it in r.json()
            if "pull_request" not in it
        ]

    async def get_user(self, login: str, installation_id: int) -> dict:
        if self.mock_mode:
            return {**MOCK_USER, "login": login}
        r = await self._request("GET", f"/users/{login}", installation_id)
        return r.json()

    async def get_repo_file(self, repo_full_name: str, path: str, installation_id: int) -> str | None:
        """Returns file contents as text, or None if not found."""
        if self.mock_mode:
            if path == ".github/prgenie.yml":
                return MOCK_PRGENIE_YML
            return None
        try:
            r = await self._request(
                "GET",
                f"/repos/{repo_full_name}/contents/{path}",
                installation_id,
                accept="application/vnd.github.raw",
            )
            return r.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise


# ---------------------------------------------------------------------------
# Module-level singleton (lazy)
# ---------------------------------------------------------------------------

_client: GitHubClient | None = None


def get_github_client() -> GitHubClient:
    global _client
    if _client is None:
        _client = GitHubClient()
    return _client


def reset_github_client() -> None:
    """For tests."""
    global _client
    _client = None
