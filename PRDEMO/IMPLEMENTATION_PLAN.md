# PRDEMO — Implementation Plan

## Build Order

Follow phases in sequence. Each phase ends with a demoable state in MOCK_MODE.
Never move to the next phase until current phase works end-to-end.

---

## Phase 0 — Project Scaffold (15 min)

Create the full directory structure:

```
PRDEMO/
├── backend/
│   ├── agents/
│   ├── nemo_claw/
│   ├── llm/
│   ├── db/
│   └── routers/
├── tests/
│   └── mock_payloads/
└── .github/
```

Files to create:
- `requirements.txt` — see CLAUDE.md for full list
- `.env.example` — see CLAUDE.md for all variables
- `backend/config.py` — Pydantic Settings reading from .env
- `backend/main.py` — FastAPI app with lifespan, includes routers
- `backend/routers/health.py` — `GET /health` returns `{"status": "ok"}`
- `backend/__init__.py`, all other `__init__.py` files

Verify: `uvicorn backend.main:app --reload` starts without errors, `/health` returns 200.

---

## Phase 1 — GitHub Webhook Receiver (25 min)

Files to create/fill:
- `backend/routers/webhook.py` — `POST /webhook`
- `backend/webhook_handler.py` — routes events to agents
- `tests/mock_payloads/pr_opened.json` — copy a real GitHub PR webhook payload
- `tests/mock_payloads/issue_created.json` — copy a real GitHub issue webhook payload

Implementation steps:

1. In `routers/webhook.py`:
   - Receive raw body + `X-Hub-Signature-256` header
   - Verify HMAC signature against `GITHUB_WEBHOOK_SECRET`
   - Return 401 if invalid, 200 if valid
   - Parse `X-GitHub-Event` header
   - Call `webhook_handler.route_event(event_type, payload)`

2. In `webhook_handler.py`:
   - Route `pull_request` events with action `opened/synchronize/reopened` → `handle_pr_event(payload)`
   - Route `issue_comment` events with body starting `/prclaw` → `handle_command(payload)`
   - Route `issues` events → `handle_issue_event(payload)`
   - Route `pull_request_review` submitted → `handle_review_ingestion(payload)` (for persona learning)
   - All handlers are stubs returning `{"ok": True}` for now

3. Test: POST mock payload to `/webhook` with correct HMAC, verify routing works.

---

## Phase 2 — Database Setup (15 min)

Files to create/fill:
- `backend/db/models.py` — all 4 SQLModel tables (see CLAUDE.md)
- `backend/db/store.py` — CRUD functions for each model

Store functions needed:
```python
# Persona
upsert_persona(repo_full_name, persona_data) -> MaintainerPersona
get_persona(repo_full_name) -> MaintainerPersona | None

# Trust
upsert_trust(login, repo_full_name, trust_data) -> ContributorTrust
get_trust(login, repo_full_name) -> ContributorTrust | None

# PR Analysis
save_pr_analysis(pr_number, repo_full_name, analysis_data) -> PRAnalysis
get_pr_analysis(pr_number, repo_full_name) -> PRAnalysis | None

# Issue Score
upsert_issue_score(issue_number, repo_full_name, score_data) -> IssueScore
get_high_demand_issues(repo_full_name, threshold) -> list[IssueScore]
get_unclustered_issues(repo_full_name) -> list[IssueScore]
```

In `backend/main.py` lifespan: `SQLModel.metadata.create_all(engine)` on startup.

---

## Phase 3 — GitHub Client (30 min)

Files to create/fill:
- `backend/github_client.py`

This is the most important infrastructure file. Implement:

```python
class GitHubClient:
    # Authentication
    def get_installation_token(self, installation_id: int) -> str
        # Generate GitHub App JWT, exchange for installation access token
        # Cache token with expiry
    
    def get_repo(self, repo_full_name: str, installation_id: int) -> Repository
    
    # PR operations
    def get_pr_diff(self, repo, pr_number: int) -> str
    def get_pr_files(self, repo, pr_number: int) -> list[dict]
    def post_pr_comment(self, repo, pr_number: int, body: str) -> int  # returns comment_id
    def create_check_run(self, repo, pr, title: str, summary: str, conclusion: str) -> int
    def submit_pr_review(self, repo, pr_number: int, body: str, comments: list[dict], event: str) -> None
        # event: "COMMENT" | "REQUEST_CHANGES" | "APPROVE"
        # comments: [{"path": "file.py", "line": 42, "body": "comment text"}]
    def add_labels(self, repo, issue_or_pr_number: int, labels: list[str]) -> None
    def ensure_labels_exist(self, repo, labels: dict[str, str]) -> None
        # labels: {"trust:high": "2ecc71", "risk:medium": "f39c12", ...}
    
    # Issue operations
    def post_issue_comment(self, repo, issue_number: int, body: str) -> int
    
    # Data fetching for agents
    def get_contributor_prs(self, repo, login: str, limit: int = 20) -> list[dict]
        # Returns: [{"number", "state", "merged", "created_at", "merged_at"}]
    def get_maintainer_reviews(self, repo, login: str, limit: int = 50) -> list[dict]
        # Returns: [{"pr_number", "body", "state", "comments": [...]}]
    def get_file_commits(self, repo, file_path: str, limit: int = 50) -> list[dict]
        # Returns: [{"author_login", "date", "message"}]
    def get_open_issues(self, repo) -> list[dict]
```

For GitHub App JWT, use the `cryptography` package:
```python
import jwt, time
from cryptography.hazmat.primitives import serialization

def generate_app_jwt(app_id: str, private_key_path: str) -> str:
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    payload = {"iat": int(time.time()), "exp": int(time.time()) + 540, "iss": app_id}
    return jwt.encode(payload, private_key, algorithm="RS256")
```

---

## Phase 4 — LLM Client + Mock Mode (15 min)

Files to create/fill:
- `backend/llm/client.py`
- `backend/llm/prompts.py`
- `backend/llm/mock_responses.py`

In `client.py`: AsyncOpenAI client wrapping vLLM. If `MOCK_MODE=true`, import from `mock_responses.py` and return immediately.

In `prompts.py`: Define all prompt templates as Python string constants. See CLAUDE.md for exact prompts:
- `TRIAGE_PROMPT`
- `PERSONA_PROMPT`  
- `REVIEW_COMMENT_PROMPT`
- `CLUSTER_PROMPT`

In `mock_responses.py`: Define realistic mock returns for each prompt type. See CLAUDE.md for mock data.

---

## Phase 5 — Trust Scorer (20 min)

File: `backend/agents/trust_scorer.py`

```python
async def compute_trust(login: str, repo_full_name: str, github: GitHubClient, installation_id: int) -> dict:
```

Steps:
1. Check DB cache — if updated within 24h, return cached
2. Fetch contributor's PRs to this repo (last 20) via `github.get_contributor_prs()`
3. Compute signals: merge_rate, avg_response_hours, resolution_rate, account_age_days
4. Apply formula from CLAUDE.md
5. Map to trust_level
6. Upsert in DB
7. Return trust dict

Test: Run against mock payload data, verify scores are sensible.

---

## Phase 6 — Risk Agent (15 min)

File: `backend/agents/risk_agent.py`

```python
def compute_risk(files_changed: list[str], additions: int, deletions: int, trust_level: str, policy: dict) -> dict:
```

No async needed — pure computation.

Steps:
1. Check files against `SENSITIVE_PATHS` (hardcoded) + `policy["risk"]["escalate_on"]` (from prclaw.yml)
2. Compute base_risk from formula in CLAUDE.md
3. Map to risk_level
4. Return risk dict with `should_escalate` flag

---

## Phase 7 — NemoClaw Policy Enforcer (20 min)

File: `backend/nemo_claw/policy_enforcer.py`
File: `backend/nemo_claw/schemas.py`

In `schemas.py`: Pydantic model for the prclaw.yml structure.

In `policy_enforcer.py`:

```python
class PolicyEnforcer:
    def __init__(self, policy: dict):
        self.policy = policy  # merged: DEFAULT_POLICY + repo prclaw.yml
    
    @classmethod
    async def from_repo(cls, repo, github: GitHubClient) -> "PolicyEnforcer":
        # Try to fetch .github/prclaw.yml from repo
        # Parse with pyyaml
        # Merge with DEFAULT_POLICY (repo overrides defaults)
        # Return PolicyEnforcer(merged_policy)
    
    def can_post_comment(self) -> bool: ...  # always True (informational)
    def can_apply_label(self, label: str) -> bool: ...
    def can_submit_review(self, triggered_by_command: bool) -> bool:
        return triggered_by_command  # only allowed if human typed /prclaw review
    def should_escalate(self, risk_level: str, trust_level: str) -> bool: ...
    def get_demand_threshold(self) -> int: ...
    def validate_review_comment(self, comment: str) -> tuple[bool, str]:
        # Check for harsh language patterns
        # Check comment is not empty
        # Returns (is_valid, reason_if_invalid)
    def is_action_forbidden(self, action: str) -> bool:
        return action in self.policy.get("forbidden", [])
```

---

## Phase 8 — Reviewer Suggester (20 min)

File: `backend/agents/reviewer_suggester.py`

```python
async def suggest_reviewer(repo_full_name: str, files_changed: list[str], pr_author: str, github: GitHubClient, installation_id: int) -> str | None:
```

Steps:
1. For each file in `files_changed` (limit to first 10 files):
   - Call `github.get_file_commits(repo, file, limit=30)`
   - Count commits per author
   - `ownership[author] += commit_count / total_commits_on_file`
2. Remove PR author from candidates
3. Sort by ownership score descending
4. Return top candidate login, or None if no clear owner

---

## Phase 9 — Persona Extractor (25 min)

File: `backend/agents/persona_extractor.py`

```python
async def extract_persona(repo_full_name: str, maintainer_login: str, github: GitHubClient, llm: LLMClient, installation_id: int) -> dict:
```

Steps:
1. Check DB — if persona exists and updated within 7 days, return cached
2. Fetch maintainer's last 50 reviews via `github.get_maintainer_reviews()`
3. Format reviews as text (PR title + review body + comment bodies, truncated)
4. Call LLM with `PERSONA_PROMPT` → parse JSON
5. Upsert in DB
6. Return persona dict

Handle: maintainer_login needs to be determined. On install, the installing user is the maintainer. Store this on install event.

---

## Phase 10 — Triage Agent (30 min)

File: `backend/agents/triage_agent.py`

```python
async def analyze_pr(pr_data: dict, persona: dict, trust: dict, risk: dict, reviewer: str | None, llm: LLMClient) -> dict:
```

Steps:
1. Build prompt from `TRIAGE_PROMPT` template, inject all context
2. Truncate diff to 3000 chars if needed (keep first 1500 + last 1500)
3. Call LLM → parse JSON response
4. Validate output against expected schema
5. Return analysis dict

Also implement `format_triage_comment(analysis, trust, risk, reviewer) -> str` that generates the full bot comment markdown from `PR_TRIAGE_COMMENT` template.

---

## Phase 11 — Wire Up PR Pipeline (20 min)

In `webhook_handler.py`, fill in `handle_pr_event(payload)`:

```python
async def handle_pr_event(payload: dict):
    repo_full_name = payload["repository"]["full_name"]
    installation_id = payload["installation"]["id"]
    pr = payload["pull_request"]
    author = pr["user"]["login"]
    pr_number = pr["number"]
    
    # 1. Get GitHub client + policy
    github = get_github_client()
    repo = github.get_repo(repo_full_name, installation_id)
    policy = await PolicyEnforcer.from_repo(repo, github)
    
    # 2. Run agents
    trust = await compute_trust(author, repo_full_name, github, installation_id)
    files = await github.get_pr_files(repo, pr_number)
    file_names = [f["filename"] for f in files]
    diff = await github.get_pr_diff(repo, pr_number)
    risk = compute_risk(file_names, pr["additions"], pr["deletions"], trust["trust_level"], policy.policy)
    reviewer = await suggest_reviewer(repo_full_name, file_names, author, github, installation_id)
    persona = await extract_persona(repo_full_name, get_maintainer_login(repo_full_name), github, llm, installation_id)
    analysis = await analyze_pr({"diff": diff, "title": pr["title"], "body": pr["body"], ...}, persona, trust, risk, reviewer, llm)
    
    # 3. Post to GitHub
    await github.ensure_labels_exist(repo, LABEL_COLORS)
    await github.add_labels(repo, pr_number, [f"trust:{trust['trust_level']}", f"risk:{risk['risk_level']}"])
    
    check_run_id = await github.create_check_run(repo, pr, 
        title=f"PRClaw: Trust {trust['trust_level'].upper()} | Risk {risk['risk_level'].upper()}",
        summary=format_check_run_summary(analysis, trust, risk),
        conclusion="neutral"  # never block — informational only
    )
    
    comment_id = await github.post_pr_comment(repo, pr_number, format_triage_comment(analysis, trust, risk, reviewer))
    
    # 4. Save analysis
    save_pr_analysis(pr_number, repo_full_name, {**analysis, "trust_level": trust["trust_level"], "risk_level": risk["risk_level"], "check_run_id": check_run_id, "bot_comment_id": comment_id})
```

Test: POST mock `pr_opened.json` to `/webhook`, verify comment + check run would be created.

---

## Phase 12 — Review Commenter + /prclaw command (30 min)

File: `backend/agents/review_commenter.py`

```python
async def generate_review(pr_diff: str, persona: dict, concerns: list[str], policy: PolicyEnforcer, llm: LLMClient) -> dict:
    # For each concern, generate a positioned inline comment
    # Returns: {"comments": [{"path", "line", "body"}], "verdict": "REQUEST_CHANGES|COMMENT"}
```

In `webhook_handler.py`, fill in `handle_command(payload)`:

```python
async def handle_command(payload: dict):
    body = payload["comment"]["body"].strip()
    
    if body.startswith("/prclaw review"):
        pr_number = payload["issue"]["number"]  # issue_comment on a PR
        repo_full_name = payload["repository"]["full_name"]
        installation_id = payload["installation"]["id"]
        
        # Check policy: only if human command
        if not policy.can_submit_review(triggered_by_command=True):
            return
        
        # Fetch cached analysis
        analysis = get_pr_analysis(pr_number, repo_full_name)
        if not analysis:
            await github.post_pr_comment(repo, pr_number, "⚠️ No PRClaw analysis found for this PR. It may still be processing.")
            return
        
        # Generate review
        diff = await github.get_pr_diff(repo, pr_number)
        persona = get_persona(repo_full_name)
        review = await generate_review(diff, persona, json.loads(analysis.concerns), policy, llm)
        
        # Validate each comment via NemoClaw
        valid_comments = []
        for comment in review["comments"]:
            is_valid, reason = policy.validate_review_comment(comment["body"])
            if is_valid:
                valid_comments.append(comment)
        
        # Submit
        await github.submit_pr_review(repo, pr_number, 
            body=f"AI-assisted review based on maintainer persona.\n\n{analysis.summary}",
            comments=valid_comments,
            event=review["verdict"]
        )
    
    elif body.startswith("/prclaw assign"):
        # Parse @username, call github.assign_reviewer
        pass
```

---

## Phase 13 — Issue Demand Agent (25 min)

File: `backend/agents/issue_demand_agent.py`

```python
async def score_issue(issue_data: dict, repo_full_name: str, github: GitHubClient, installation_id: int) -> dict:

async def cluster_issues(repo_full_name: str, llm: LLMClient) -> None:
    # Fetch unclustered issues from DB
    # Build batch for LLM
    # Parse cluster assignments
    # Update cluster_id on each IssueScore
    # Post cluster comment on highest-demand issue per cluster
```

In `webhook_handler.py`, fill in `handle_issue_event(payload)`:
- Score the issue
- Apply demand label
- If demand == "high", post demand signal comment

Add background task in `main.py` lifespan that calls `cluster_issues()` every 15 minutes using `asyncio` or `apscheduler`.

---

## Phase 14 — Mock Demo Polish (20 min)

Goal: full end-to-end demo with `MOCK_MODE=true` and no live GitHub App.

Create `tests/demo_runner.py`:
```python
# Simulates GitHub webhook events hitting the API
# Posts mock payloads to localhost:8080/webhook
# Prints what would have been posted to GitHub
```

Create mock webhook sender that replays `pr_opened.json` and `issue_created.json`.

Verify:
- [ ] PR opened → trust score + risk + triage comment printed
- [ ] `/prclaw review` command → inline review comments printed
- [ ] Issue opened → demand score + label printed
- [ ] Issue cluster batch → cluster assignments printed
- [ ] All outputs respect policy (no forbidden actions triggered)

---

## Phase 15 — Live GitHub App (if GPU available) (30 min)

1. Register GitHub App at github.com/settings/apps/new
2. Set webhook URL to `https://<brev-tunnel>/webhook`
3. Download private key PEM
4. Set permissions (see ARCHITECTURE.md)
5. Install app on demo repo
6. Set `MOCK_MODE=false`, set `VLLM_BASE_URL` to Brev endpoint
7. Open a real PR on demo repo
8. Watch triage comment appear

---

## Label Color Reference

```python
LABEL_COLORS = {
    "trust:high":     "2ecc71",  # green
    "trust:medium":   "f1c40f",  # yellow
    "trust:new":      "95a5a6",  # grey
    "trust:flagged":  "e74c3c",  # red
    "risk:low":       "2ecc71",  # green
    "risk:medium":    "e67e22",  # orange
    "risk:high":      "e74c3c",  # red
    "risk:critical":  "8e44ad",  # purple
    "demand:high":    "e74c3c",  # red
    "demand:medium":  "e67e22",  # orange
    "demand:low":     "2ecc71",  # green
}
```

---

## Checklist Before Demo

- [ ] MOCK_MODE works end-to-end (all agents produce output)
- [ ] Webhook signature verification working
- [ ] All 4 DB tables created and populated correctly
- [ ] Triage comment posts correct trust badge + risk badge + checklist
- [ ] `/prclaw review` command triggers inline review generation
- [ ] Issue demand scoring labels issues correctly
- [ ] NemoClaw forbidden list blocks merge/close actions
- [ ] prclaw.yml in demo repo customizes behavior
- [ ] All bot comments include AI disclosure footer
- [ ] Check run created with correct conclusion status
