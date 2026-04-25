# PRDEMO — Coding Session Instructions

## What This Project Is

**PRClaw** is a GitHub-native AI agent that:
1. Learns how a specific maintainer reviews code (Persona Extractor)
2. Scores contributor trust based on GitHub history (Trust Scorer)
3. Triages every incoming PR with summary, risk, checklist, reviewer suggestion (Triage Agent)
4. Flags risky PRs — large diffs from unknown contributors touching sensitive files (Risk Agent)
5. Scores and clusters open issues by community demand (Issue Demand Agent)
6. Suggests reviewers based on file ownership from git blame (Reviewer Suggester)
7. Posts persona-voiced inline review comments when maintainer types `/prclaw review` (Review Commenter)

Everything surfaces **inside GitHub** — no separate frontend.
- Triage output → GitHub Check Run + bot comment on PR
- Risk escalation → `risk:high` label + escalation mention
- Issue demand → `demand:high/medium/low` label + cluster comment
- Review comments → formal GitHub PR review (only on `/prclaw review` command)

NemoClaw policy lives in `.github/prclaw.yml` in each repo. The agent reads this file to configure per-repo behavior.

---

## Project Location

`D:\Redhat Hackathon\PRDEMO\`

---

## Final File Structure to Build

```
PRDEMO/
├── backend/
│   ├── main.py                        # FastAPI app, mounts all routers
│   ├── config.py                      # Pydantic Settings, reads .env
│   ├── webhook_handler.py             # Routes GitHub webhook events
│   ├── github_client.py               # PyGitHub wrapper + all GitHub API calls
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── persona_extractor.py       # Reads past reviews → builds maintainer profile
│   │   ├── trust_scorer.py            # Rule-based contributor trust scoring
│   │   ├── triage_agent.py            # PR summary + priority + concerns + checklist
│   │   ├── risk_agent.py              # Sensitive file detection + risk level
│   │   ├── reviewer_suggester.py      # git blame file ownership analysis
│   │   ├── review_commenter.py        # Persona-voiced inline review comments
│   │   └── issue_demand_agent.py      # Issue scoring + semantic clustering
│   ├── nemo_claw/
│   │   ├── __init__.py
│   │   ├── policy_enforcer.py         # Reads .github/prclaw.yml, enforces rules
│   │   └── schemas.py                 # Pydantic models for policy YAML
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py                  # vLLM OpenAI-compatible client wrapper
│   │   ├── prompts.py                 # All prompt templates as constants
│   │   └── mock_responses.py          # Mock LLM responses for demo without GPU
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py                  # SQLModel table definitions
│   │   └── store.py                   # CRUD helpers
│   └── routers/
│       ├── __init__.py
│       ├── webhook.py                 # POST /webhook
│       └── health.py                  # GET /health
├── .github/
│   └── prclaw.yml                     # Sample NemoClaw policy (for demo repo)
├── tests/
│   ├── test_trust_scorer.py
│   ├── test_triage_agent.py
│   └── mock_payloads/
│       ├── pr_opened.json             # Sample GitHub PR webhook payload
│       └── issue_created.json         # Sample GitHub issue webhook payload
├── requirements.txt
├── .env.example
├── ARCHITECTURE.md
├── IMPLEMENTATION_PLAN.md
└── CLAUDE.md                          # This file
```

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI + Python 3.11 | Fast, async, easy webhook handling |
| GitHub API | PyGitHub + httpx | PyGitHub for REST, httpx for raw API calls |
| LLM | vLLM (OpenAI-compatible) on Brev | Nemotron-Nano-4B or Nemotron-Mini-4B |
| Database | SQLite + SQLModel | Zero config, sufficient for demo |
| Policy | YAML (pyyaml) | NemoClaw policy per repo |
| Webhook auth | hmac + sha256 | GitHub's standard |

---

## Environment Variables (.env.example)

```
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY_PATH=./github-app.pem
GITHUB_WEBHOOK_SECRET=your_webhook_secret
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL=nvidia/Nemotron-Mini-4B-Instruct
MOCK_MODE=true
DATABASE_URL=sqlite:///./prdemo.db
PORT=8080
```

`MOCK_MODE=true` makes every LLM call return pre-written mock responses — demo works without GPU.

---

## GitHub App Permissions Required

**Repository permissions:**
- Contents: Read (for diffs, git blame)
- Pull requests: Read & Write (post reviews, comments)
- Issues: Read & Write (post comments, apply labels)
- Checks: Write (create check runs)
- Metadata: Read

**Subscribed webhook events:**
- `pull_request` (opened, synchronize, reopened, closed)
- `pull_request_review` (submitted — for persona learning)
- `issues` (opened, edited, closed)
- `issue_comment` (created — for `/prclaw` commands)

---

## Data Models (db/models.py)

```python
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
import json

class MaintainerPersona(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    repo_full_name: str = Field(index=True)   # "owner/repo"
    maintainer_login: str
    focus: str           # JSON list: ["correctness", "tests"]
    strictness: float    # 0.0-1.0
    tone: str            # "constructive but direct"
    avg_comments_per_pr: float
    common_phrases: str  # JSON list
    tolerance: str       # JSON dict: {"missing_tests": "low"}
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ContributorTrust(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    login: str = Field(index=True)
    repo_full_name: str = Field(index=True)
    trust_level: str     # "high" | "medium" | "new" | "flagged"
    trust_score: float   # 0.0-1.0
    signals: str         # JSON dict
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PRAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pr_number: int
    repo_full_name: str = Field(index=True)
    trust_level: str
    risk_level: str      # "low" | "medium" | "high" | "critical"
    priority: str        # "low" | "medium" | "high"
    summary: str
    concerns: str        # JSON list
    checklist: str       # JSON list
    suggested_reviewer: Optional[str]
    check_run_id: Optional[int]
    bot_comment_id: Optional[int]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class IssueScore(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    issue_number: int
    repo_full_name: str = Field(index=True)
    demand_score: float
    neglect_score: float
    priority_score: float
    demand_level: str    # "high" | "medium" | "low"
    cluster_id: Optional[str]
    reactions: int
    unique_commenters: int
    days_open: int
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## Key Agent Logic

### Trust Scorer (trust_scorer.py)

Zero LLM. Pure rules. Fetch via GitHub API.

```python
def compute_trust(contributor_login: str, repo_full_name: str) -> dict:
    # Fetch contributor's PRs to this repo (last 20)
    # signals needed:
    #   total_prs, merged_prs, closed_without_merge
    #   avg_hours_to_respond_to_review  (from review thread timestamps)
    #   review_resolution_rate          (% requested changes they resolved)
    #   account_age_days                (from user.created_at)

    merge_rate = merged_prs / max(1, total_prs)
    response_score = min(1.0, 24 / max(1, avg_response_hours))  # 24h = 1.0
    resolution_rate = resolved_changes / max(1, total_requested_changes)
    age_score = min(1.0, account_age_days / 365)

    trust_score = (merge_rate * 0.4) + (response_score * 0.3) + (resolution_rate * 0.2) + (age_score * 0.1)

    if trust_score >= 0.75:
        trust_level = "high"
    elif trust_score >= 0.45:
        trust_level = "medium"
    elif total_prs == 0:
        trust_level = "new"
    else:
        trust_level = "flagged"

    return {"trust_level": trust_level, "trust_score": trust_score, "signals": {...}}
```

### Persona Extractor (persona_extractor.py)

One vLLM call on install + weekly refresh.

```python
PERSONA_PROMPT = """
Analyze these GitHub PR reviews written by maintainer @{login} and extract their reviewing persona.

Reviews (most recent first):
{reviews_text}

Return JSON:
{{
  "focus": ["list of what they care most about, e.g. correctness, tests, performance"],
  "strictness": 0.0-1.0,
  "tone": "one phrase describing their tone",
  "avg_comments_per_pr": float,
  "common_phrases": ["exact phrases they use repeatedly"],
  "tolerance": {{
    "missing_tests": "low|medium|high",
    "style_issues": "low|medium|high",
    "performance": "low|medium|high",
    "docs": "low|medium|high"
  }}
}}
"""
# Feed last 50 reviews (title + body of each review comment)
# Parse JSON from response
# Store in MaintainerPersona table
```

### Triage Agent (triage_agent.py)

One vLLM call per PR.

```python
TRIAGE_PROMPT = """
You are a PR triage assistant. Analyze this pull request and return structured JSON.

Maintainer cares about: {focus}
Maintainer tone: {tone}
Maintainer strictness: {strictness}/1.0

Contributor trust: {trust_level}
Trust signals: {trust_signals_text}

PR #{pr_number}: {pr_title}
Author: @{author}
Files changed: {files_list}
Lines: +{additions} -{deletions}

Diff (truncated to 3000 chars):
{diff}

Return JSON exactly:
{{
  "summary": "2-3 sentence summary of what this PR does and main finding",
  "priority": "high|medium|low",
  "concerns": ["specific concern 1", "specific concern 2"],
  "checklist": ["Reviewer action item 1", "Reviewer action item 2"],
  "suggested_action": "approve|request_changes|comment|escalate"
}}
"""
```

### Risk Agent (risk_agent.py)

No LLM. Pattern matching on changed files.

```python
SENSITIVE_PATHS = [
    "auth/", "authentication/", "login/", "oauth/",
    "crypto/", "encryption/", "security/",
    "requirements.txt", "package.json", "Pipfile", "go.mod",  # dep files
    "Dockerfile", ".github/workflows/",  # CI/CD
    "migrations/", "schema.sql",  # database
]

def compute_risk(files_changed: list, diff_size: int, trust_level: str) -> dict:
    sensitive_hits = [f for f in files_changed if any(p in f for p in SENSITIVE_PATHS)]
    
    base_risk = 0.0
    if sensitive_hits:
        base_risk += 0.4
    if diff_size > 500:
        base_risk += 0.2
    if diff_size > 1000:
        base_risk += 0.2
    if trust_level == "new":
        base_risk += 0.3
    if trust_level == "flagged":
        base_risk += 0.5

    if base_risk >= 0.8:
        risk_level = "critical"
    elif base_risk >= 0.5:
        risk_level = "high"
    elif base_risk >= 0.25:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_score": min(1.0, base_risk),
        "sensitive_files": sensitive_hits,
        "should_escalate": risk_level in ("critical", "high") and trust_level in ("new", "flagged")
    }
```

### Reviewer Suggester (reviewer_suggester.py)

No LLM. GitHub commits API.

```python
def suggest_reviewer(repo, files_changed: list, pr_author: str) -> str | None:
    # For each changed file, get last 50 commits via GitHub API
    # Count commits per author per file
    # Sum up ownership scores across all changed files
    # Subtract: authors who are already reviewing, the PR author itself
    # Sort by score
    # Return top suggestion login
    
    # ownership_score[login] += (commits_on_file / total_commits_on_file)
    # Penalize if they have > 5 open review requests currently
```

### Issue Demand Agent (issue_demand_agent.py)

Scoring is no-LLM. Clustering uses one batched vLLM call every 15 minutes.

```python
def score_issue(issue, last_maintainer_response_date) -> dict:
    reactions = issue.reactions["total_count"]
    unique_commenters = len(set(c.user.login for c in issue.get_comments()))
    days_open = (datetime.utcnow() - issue.created_at).days
    
    if last_maintainer_response_date:
        days_since_response = (datetime.utcnow() - last_maintainer_response_date).days
    else:
        days_since_response = days_open
    
    label_weight = 1.0
    labels = [l.name for l in issue.labels]
    if "bug" in labels:
        label_weight = 1.3
    elif "security" in labels:
        label_weight = 1.5
    
    demand_score = (reactions * 0.4) + (unique_commenters * 0.3) + (min(days_open/30, 1.0) * 0.2) + (label_weight * 0.1)
    neglect_score = days_since_response / max(1, 7)
    priority_score = demand_score * neglect_score
    
    if priority_score >= 8.0:
        demand_level = "high"
    elif priority_score >= 3.0:
        demand_level = "medium"
    else:
        demand_level = "low"

    return {"demand_level": demand_level, "priority_score": priority_score, ...}


CLUSTER_PROMPT = """
Cluster these GitHub issues by theme. Each issue has a number, title, and body snippet.

Issues:
{issues_json}

Return JSON:
{{
  "clusters": [
    {{
      "id": "short-kebab-case-id",
      "name": "Human readable cluster name",
      "issue_numbers": [1, 2, 3],
      "summary": "1-2 sentence description of the shared problem"
    }}
  ]
}}
"""
```

---

## NemoClaw Policy (nemo_claw/policy_enforcer.py)

Reads `.github/prclaw.yml` from the target repo via GitHub API.

```python
# Default policy if no prclaw.yml found in repo
DEFAULT_POLICY = {
    "persona": {"focus": ["correctness", "tests"], "strictness": 0.7, "tone": "constructive"},
    "trust": {"auto_label": True, "high_threshold": 0.75, "new_threshold": 0.0},
    "risk": {"auto_label": True, "escalate_on": ["auth/", "crypto/", "requirements.txt", ".github/workflows/"]},
    "demand": {"comment_threshold": 25, "cluster_min_size": 3, "auto_label": True},
    "forbidden": ["merge_pr", "close_pr", "close_issue", "post_without_disclosure"]
}

class PolicyEnforcer:
    def can_post_comment(self, context: dict) -> bool: ...
    def can_apply_label(self, label: str, context: dict) -> bool: ...
    def can_submit_review(self, context: dict) -> bool: ...
    def should_escalate(self, risk_level: str, trust_level: str) -> bool: ...
    def get_demand_threshold(self) -> float: ...
```

---

## GitHub Bot Comment Templates

### PR Triage Comment (posted automatically on PR open):

```python
PR_TRIAGE_COMMENT = """
## 🤖 PRClaw Analysis

| | |
|---|---|
| **Contributor Trust** | {trust_emoji} {trust_level_display} |
| **Risk Level** | {risk_emoji} {risk_level_display} |
| **Priority** | {priority_display} |
| **Suggested Reviewer** | {reviewer_mention} |

**Summary**
{summary}

**Review Checklist**
{checklist_items}

**Concerns**
{concern_items}

---
*Type `/prclaw review` to post inline review comments in this PR's voice.*
*Powered by [PRClaw](https://github.com/prclaw) · Policy: `.github/prclaw.yml`*
"""

TRUST_EMOJI = {"high": "🟢", "medium": "🟡", "new": "⚪", "flagged": "🔴"}
RISK_EMOJI = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🚨"}
```

### Issue Demand Comment (posted on high-demand issues):

```python
ISSUE_DEMAND_COMMENT = """
## 📊 PRClaw Demand Signal

This issue has **{reactions} reactions** and has been open for **{days_open} days**.
{maintainer_silence_text}

{cluster_section}

---
*PRClaw automatically surfaces high-demand issues. Label: `demand:{demand_level}`*
"""
```

---

## Webhook Flow

```
POST /webhook
  └── verify HMAC signature
  └── parse event type

  pull_request.opened / synchronize / reopened
    ├── trust_scorer.compute_trust(author, repo)
    ├── risk_agent.compute_risk(files, diff_size, trust_level)
    ├── reviewer_suggester.suggest(repo, files, author)
    ├── triage_agent.analyze(pr, persona, trust, risk)  # 1 LLM call
    ├── github_client.create_check_run(repo, pr, result)
    └── github_client.post_pr_comment(repo, pr, triage_comment)

  issue_comment.created  (body starts with "/prclaw")
    ├── parse command: "/prclaw review" | "/prclaw assign @user"
    ├── policy_enforcer.can_submit_review(context)
    └── if review:
          review_commenter.generate(pr, persona, concerns)  # 1 LLM call
          github_client.submit_review(repo, pr, comments, verdict)

  issues.opened / issues.edited
    ├── issue_demand_agent.score_issue(issue)
    ├── github_client.add_label(repo, issue, demand_label)
    └── if demand == "high": github_client.post_issue_comment(demand_comment)

  pull_request_review.submitted  (from real maintainer)
    └── persona_extractor.ingest_review(review)  # incremental persona update
```

---

## LLM Call Budget Per Event

| Event | LLM Calls | Notes |
|---|---|---|
| PR opened | 1 | Triage (summary + concerns + checklist) |
| `/prclaw review` | 1 | Review comment generation |
| Issue batch (every 15min) | 1 | Clustering all open issues |
| App install / weekly | 1 | Persona extraction from review history |
| **Total per PR lifecycle** | **2** | vs. naive 5-6 |

---

## Mock Mode (for demo without GPU)

In `llm/mock_responses.py`, define static responses for each prompt type. When `MOCK_MODE=true`, all LLM calls return these instantly. Demo runs end-to-end without Brev.

```python
MOCK_TRIAGE = {
    "summary": "Adds a Redis-backed caching layer to reduce repeated database queries on the /users endpoint. Main logic is sound but the implementation lacks an eviction policy and test coverage for cache invalidation.",
    "priority": "high",
    "concerns": ["No TTL or eviction policy defined", "Missing tests for cache invalidation", "No error handling for Redis connection failure"],
    "checklist": ["Define TTL for cache entries", "Add unit tests for cache miss and invalidation", "Handle Redis connection errors gracefully", "Update API docs"],
    "suggested_action": "request_changes"
}

MOCK_PERSONA = {
    "focus": ["correctness", "tests", "error handling"],
    "strictness": 0.8,
    "tone": "constructive but direct",
    "avg_comments_per_pr": 4.2,
    "common_phrases": ["edge cases?", "needs test coverage", "what happens if this fails?"],
    "tolerance": {"missing_tests": "low", "style_issues": "medium", "performance": "high", "docs": "medium"}
}
```

---

## Sample prclaw.yml (for demo repo)

```yaml
# .github/prclaw.yml
persona:
  focus:
    - correctness
    - tests
    - error_handling
  strictness: 0.8
  tone: constructive but direct

trust:
  auto_label: true
  high_threshold: 0.75

risk:
  auto_label: true
  escalate_on:
    - auth/
    - crypto/
    - requirements.txt
    - package.json
    - .github/workflows/

demand:
  comment_threshold: 25
  cluster_min_size: 3
  auto_label: true

forbidden:
  - merge_pr
  - close_pr
  - close_issue
  - post_without_ai_disclosure
```

---

## Build Order (follow exactly)

See `IMPLEMENTATION_PLAN.md` for phased build order.

Start with Phase 0 (setup) → Phase 1 (GitHub webhook) → Phase 2 (Trust Scorer) → test with mock payloads before adding LLM.

Always keep `MOCK_MODE=true` working. Every phase must be demoable in mock mode before moving on.

---

## Key Dependencies (requirements.txt)

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
PyGitHub>=2.3.0
httpx>=0.27.0
sqlmodel>=0.0.18
pyyaml>=6.0.1
python-dotenv>=1.0.1
openai>=1.30.0        # vLLM uses OpenAI-compatible API
pydantic>=2.7.0
pydantic-settings>=2.2.1
cryptography>=42.0.0  # for GitHub App JWT signing
```

---

## Hackathon Context

- Event: Red Hat / NVIDIA vLLM Hackathon, April 25 2026, Boston Seaport
- Track: Track 5 — Agentic Edge powered by NemoClaw (NVIDIA GPU Prize)
- Required: NemoClaw load-bearing, vLLM, Agentic Workflows, Tool Calling
- GPU: NVIDIA Brev (get credits from organizers), vLLM endpoint TBD
- Always keep MOCK_MODE working — never assume GPU is available for demo
- NemoClaw must be visibly enforcing policy (show the YAML, show forbidden actions)
- Pitch line: "We don't just automate PR review — we replicate how maintainers actually review, including their style, expectations, and trust in contributors."
