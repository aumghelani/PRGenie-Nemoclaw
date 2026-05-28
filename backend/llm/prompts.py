"""
All prompt templates for PRGenie, kept as plain string constants.

Three categories:
  * SYSTEM_*  — set the agent's role, identical across calls so vLLM prefix
                caching reuses the prefix tokens (this is the headline
                Inference Efficiency Impact win for Track 5 scoring).
  * USER_*    — per-call user messages with placeholders.
  * TRIAGE_TOOL_SCHEMAS — JSON schemas the Triage Agent passes to vLLM
                via the OpenAI tool_calling API. The model can choose to
                call `submit_triage` to return its structured analysis.

Use Python `.format(**ctx)` to fill placeholders, NEVER f-strings at module
load time — placeholders must stay literal until call time.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# System prompts — long, stable, cache-friendly.
# ---------------------------------------------------------------------------

SYSTEM_TRIAGE = """You are PRGenie, an AI pull-request triage assistant operating inside a GitHub App.

Your job: read a pull request and produce a STRUCTURED analysis that helps the maintainer decide what to do next. You are not the maintainer; you assist them.

Hard rules:
  - You MUST call the `submit_triage` tool with valid JSON. Never reply with prose.
  - You MAY NOT recommend `merge` or `close` actions. Allowed actions: approve, request_changes, comment, escalate.
  - Be specific. "Add tests" is bad; "Add a test for the cache invalidation path when Redis returns nil" is good.
  - Calibrate your tone to the maintainer persona provided. If their tone is "constructive but direct", do not be flowery.
  - If the diff is trivial (docs, typos), priority is `low` and concerns may be empty.
"""

SYSTEM_PERSONA = """You are PRGenie's Persona Extractor. Given a maintainer's recent code reviews, infer their reviewing persona.

Hard rules:
  - Output ONLY behavioral signals derived from the review TEXT itself. Never infer based on identity, name, organization, or anything outside the review content.
  - You MUST call the `submit_persona` tool with valid JSON.
  - `common_phrases` must be EXACT verbatim quotes from the reviews, not paraphrases.
"""

SYSTEM_REVIEW = """You are PRGenie, writing a formal GitHub PR review IN THE VOICE of the maintainer whose persona is provided.

Hard rules:
  - You MUST call the `submit_review` tool with valid JSON.
  - Each comment MUST be tied to a specific file path and line number from the diff.
  - Constructive only. No insults, no dismissive language. Cite specific code or behavior.
  - Verdict can ONLY be `COMMENT` or `REQUEST_CHANGES`. NEVER `APPROVE`.
  - Use the maintainer's `common_phrases` where natural, but do not parrot them in every comment.
"""

SYSTEM_CLUSTER = """You are PRGenie's Issue Demand Agent. Given a list of open GitHub issues, group them by theme.

Hard rules:
  - You MUST call the `submit_clusters` tool with valid JSON.
  - Only group issues that share a real underlying problem. Do not invent connections.
  - `cluster_id` must be short kebab-case (e.g. "redis-cache-bug").
  - It is acceptable for some issues to remain UNGROUPED if no good cluster exists.
"""


# ---------------------------------------------------------------------------
# User-message templates.
# ---------------------------------------------------------------------------

USER_TRIAGE = """Maintainer persona:
  focus: {focus}
  tone: {tone}
  strictness: {strictness}/1.0
  common_phrases: {common_phrases}

Contributor trust: {trust_level} (score {trust_score:.2f})
Trust signals: {trust_signals}

Risk profile: {risk_level} (score {risk_score:.2f})
Sensitive files touched: {sensitive_files}

Suggested reviewer (file ownership): {suggested_reviewer}

PR #{pr_number}: {pr_title}
Author: @{author}
Files changed ({files_count}): {files_list}
Lines: +{additions} -{deletions}

Diff (truncated):
```diff
{diff}
```

Call `submit_triage` with your structured analysis."""

USER_PERSONA = """Maintainer: @{login}
Reviews ({review_count} most recent first):

{reviews_text}

Call `submit_persona` with the inferred persona."""

USER_REVIEW = """Maintainer persona:
  focus: {focus}
  tone: {tone}
  common_phrases: {common_phrases}

Existing triage concerns to ground the review in:
{concerns}

Diff:
```diff
{diff}
```

Generate inline review comments. Each comment must be on a real line in the diff above. Call `submit_review` when done."""

USER_CLUSTER = """Open issues to cluster (one per line):

{issues_text}

Call `submit_clusters` with your grouping. Minimum cluster size: {min_size}."""


# ---------------------------------------------------------------------------
# Tool schemas — vLLM is started with --enable-auto-tool-choice
# --tool-call-parser qwen3_coder, so Nemotron will emit structured calls.
# ---------------------------------------------------------------------------

TRIAGE_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_triage",
        "description": "Submit the structured PR triage analysis.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "2-3 sentence summary of what this PR does and the main finding."},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                "concerns": {"type": "array", "items": {"type": "string"}, "description": "Specific concerns about correctness, tests, security, or design."},
                "checklist": {"type": "array", "items": {"type": "string"}, "description": "Action items the human reviewer should verify."},
                "suggested_action": {"type": "string", "enum": ["approve", "request_changes", "comment", "escalate"]},
            },
            "required": ["summary", "priority", "concerns", "checklist", "suggested_action"],
        },
    },
}

PERSONA_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_persona",
        "description": "Submit the inferred maintainer persona.",
        "parameters": {
            "type": "object",
            "properties": {
                "focus": {"type": "array", "items": {"type": "string"}},
                "strictness": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "tone": {"type": "string"},
                "avg_comments_per_pr": {"type": "number"},
                "common_phrases": {"type": "array", "items": {"type": "string"}},
                "tolerance": {
                    "type": "object",
                    "properties": {
                        "missing_tests": {"type": "string", "enum": ["low", "medium", "high"]},
                        "style_issues": {"type": "string", "enum": ["low", "medium", "high"]},
                        "performance": {"type": "string", "enum": ["low", "medium", "high"]},
                        "docs": {"type": "string", "enum": ["low", "medium", "high"]},
                    },
                },
            },
            "required": ["focus", "strictness", "tone", "common_phrases", "tolerance"],
        },
    },
}

REVIEW_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_review",
        "description": "Submit inline review comments and an overall verdict.",
        "parameters": {
            "type": "object",
            "properties": {
                "comments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "line": {"type": "integer"},
                            "body": {"type": "string"},
                        },
                        "required": ["path", "line", "body"],
                    },
                },
                "verdict": {"type": "string", "enum": ["COMMENT", "REQUEST_CHANGES"]},
            },
            "required": ["comments", "verdict"],
        },
    },
}

CLUSTER_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_clusters",
        "description": "Submit the issue clustering result.",
        "parameters": {
            "type": "object",
            "properties": {
                "clusters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "short kebab-case id"},
                            "name": {"type": "string"},
                            "issue_numbers": {"type": "array", "items": {"type": "integer"}},
                            "summary": {"type": "string"},
                        },
                        "required": ["id", "name", "issue_numbers", "summary"],
                    },
                },
            },
            "required": ["clusters"],
        },
    },
}
