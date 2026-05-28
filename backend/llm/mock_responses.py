"""
Mock LLM responses — used when MOCK_MODE=true (no GPU / no Brev).

The keys are the `tool_name` the LLMClient would have called. Each value is
the JSON the model would have returned via that tool — already parsed.
LLMClient.complete_tool() returns these directly when in mock mode.

Crafted to match the demo PR (Redis-cache PR #42 from github_client mock data)
so the end-to-end mock walkthrough tells a coherent story.
"""
from __future__ import annotations

MOCK_TRIAGE = {
    "summary": (
        "Adds a Redis-backed caching layer to the /users endpoint to reduce database load. "
        "The core implementation is sound but ships without an eviction policy and lacks "
        "tests for cache invalidation."
    ),
    "priority": "high",
    "concerns": [
        "No TTL or eviction policy defined — cache will grow unbounded",
        "Missing tests for cache invalidation on user updates",
        "No error handling if Redis connection fails — request will 500",
        "Adds redis to requirements.txt but no version pin",
    ],
    "checklist": [
        "Define TTL for cache entries (e.g. r.set(..., ex=3600))",
        "Add unit tests covering cache miss, cache hit, and stale-on-update",
        "Wrap Redis calls in try/except so DB still serves on Redis outage",
        "Pin redis>=5.0,<6 in requirements.txt",
    ],
    "suggested_action": "request_changes",
}

MOCK_PERSONA = {
    "focus": ["correctness", "tests", "error_handling"],
    "strictness": 0.8,
    "tone": "constructive but direct",
    "avg_comments_per_pr": 4.2,
    "common_phrases": [
        "edge cases?",
        "needs test coverage",
        "what happens if this fails?",
        "what if Redis is down",
    ],
    "tolerance": {
        "missing_tests": "low",
        "style_issues": "medium",
        "performance": "high",
        "docs": "medium",
    },
}

MOCK_REVIEW = {
    "comments": [
        {
            "path": "app/cache.py",
            "line": 5,
            "body": (
                "What if Redis is down? This call will raise and the whole /users request will 500. "
                "Wrap the get/set in try/except and fall back to db.fetch_user."
            ),
        },
        {
            "path": "app/cache.py",
            "line": 9,
            "body": (
                "`r.set(...)` without an `ex=` means this entry lives forever. "
                "Stale data will be served on user updates. Set a TTL — `ex=3600` is a reasonable default."
            ),
        },
        {
            "path": "tests/test_users.py",
            "line": 1,
            "body": "Edge cases? I don't see a test for the cache-invalidation path when a user is updated.",
        },
        {
            "path": "requirements.txt",
            "line": 1,
            "body": "Pin a version range here — `redis>=5.0,<6`. Unpinned deps bite us on transitive upgrades.",
        },
    ],
    "verdict": "REQUEST_CHANGES",
}

MOCK_CLUSTERS = {
    "clusters": [
        {
            "id": "redis-cache-bug",
            "name": "Redis cache invalidation / eviction problems",
            "issue_numbers": [91],
            "summary": "Redis-backed caching is missing TTL and invalidation. Multiple users hit stale data after updates.",
        },
        {
            "id": "login-special-chars",
            "name": "Login fails on special characters in email",
            "issue_numbers": [88, 95],
            "summary": "The login endpoint 500s when the email contains '+' or unicode. Likely the same input-validation bug.",
        },
    ],
}


# Map tool name → mock return.
MOCK_BY_TOOL = {
    "submit_triage": MOCK_TRIAGE,
    "submit_persona": MOCK_PERSONA,
    "submit_review": MOCK_REVIEW,
    "submit_clusters": MOCK_CLUSTERS,
}
