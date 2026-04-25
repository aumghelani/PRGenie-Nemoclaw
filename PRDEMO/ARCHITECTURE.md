# PRDEMO — Architecture

## Overview

PRClaw is a GitHub App (webhook-driven backend) that installs on any GitHub repository and surfaces AI-powered PR triage, contributor trust scoring, and issue demand analysis entirely within GitHub's native UI.

No separate frontend. Everything appears as GitHub Check Runs, bot comments, PR reviews, and labels.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub                                    │
│                                                                  │
│  PR opened ──────────────────────────────────────────────────┐  │
│  Issue created ───────────────────────────────────────────┐  │  │
│  /prclaw comment ──────────────────────────────────────┐  │  │  │
│                                                         │  │  │  │
└─────────────────────────────────────────────────────────┼──┼──┼──┘
                                                          │  │  │
                                        Webhooks (HMAC)  │  │  │
                                                          ▼  ▼  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                               │
│                                                                  │
│  POST /webhook                                                   │
│       │                                                          │
│       ├── webhook_handler.py                                     │
│       │        routes by event type                              │
│       │                                                          │
│  ┌────┴──────────────────────────────────────────────────────┐  │
│  │                    Agent Pipeline                          │  │
│  │                                                            │  │
│  │  on PR opened:                                             │  │
│  │    TrustScorer ──► RiskAgent ──► ReviewerSuggester        │  │
│  │         └──────────────────────────► TriageAgent ──► Post  │  │
│  │                                           │                │  │
│  │  on /prclaw review:                       ▼                │  │
│  │    PersonaExtractor ──► ReviewCommenter ──► Submit Review  │  │
│  │                                                            │  │
│  │  on issue event:                                           │  │
│  │    IssueDemandAgent ──► Label + Comment                    │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  NemoClaw Layer │  │  LLM Client  │  │   SQLite / DB      │  │
│  │  policy_enforcer│  │  vLLM API    │  │  Persona cache     │  │
│  │  prclaw.yml     │  │  MOCK_MODE   │  │  Trust scores      │  │
│  └─────────────────┘  └──────────────┘  │  PR analyses       │  │
│                                         │  Issue scores      │  │
└─────────────────────────────────────────┴────────────────────┴──┘
                                                    │
                              GitHub API (PyGitHub) │
                                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub                                    │
│                                                                  │
│  ✓ Check Run posted     ✓ Bot comment on PR                      │
│  ✓ Labels applied       ✓ Inline review comments                 │
│  ✓ Issue demand label   ✓ Issue cluster comment                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Design

### 1. Persona Extractor
**Trigger:** GitHub App install on repo + weekly cron  
**Input:** Last 50 PR reviews submitted by the maintainer  
**Output:** `MaintainerPersona` stored in DB  
**LLM:** 1 call  
**NemoClaw:** Only behavioral signals, no personal/identity inference forbidden

### 2. Trust Scorer
**Trigger:** Every PR open event  
**Input:** PR author's GitHub history in this repo  
**Output:** `ContributorTrust` — `high / medium / new / flagged`  
**LLM:** None — pure rule engine  
**NemoClaw:** Forbidden signals: name, org, nationality, account photo

### 3. Triage Agent
**Trigger:** PR opened, synchronized, reopened  
**Input:** PR diff + persona profile + trust score + risk assessment  
**Output:** Summary, priority, concerns, checklist, suggested action  
**LLM:** 1 call  
**NemoClaw:** Output schema validated before posting; no merge/close permissions

### 4. Risk Agent
**Trigger:** Runs inline during Triage  
**Input:** Changed files list + diff size + trust level  
**Output:** Risk level `low/medium/high/critical` + sensitive files list  
**LLM:** None — pattern matching on file paths  
**NemoClaw:** Escalation is the only auto-action gated at `critical` + `new/flagged` contributor

### 5. Reviewer Suggester
**Trigger:** Runs inline during Triage  
**Input:** Changed files, PR author login  
**Output:** Top 1-2 suggested reviewer logins  
**LLM:** None — GitHub commits API + ownership scoring  
**NemoClaw:** Cannot suggest reviewers with documented conflict threads with PR author

### 6. Review Commenter
**Trigger:** Maintainer posts comment `/prclaw review` on a PR  
**Input:** PR diff + persona profile + triage concerns  
**Output:** Inline review comments + overall verdict  
**LLM:** 1 call  
**NemoClaw:** `tone: constructive_only`, `evidence_required: true`, human command = approval gate

### 7. Issue Demand Agent
**Trigger:** Issue created, issue reacted to, issue commented on  
**Clustering:** Batched every 15 minutes across all open issues  
**Input:** Issue reactions, commenter count, age, maintainer response history  
**Output:** Demand level + label + cluster membership  
**LLM:** 1 batched call for clustering only  
**NemoClaw:** Trust-neutral — score by community engagement only, not who filed

---

## Data Flow: PR Opened

```
1. GitHub sends webhook: pull_request.opened
2. Verify HMAC signature
3. Extract: repo, PR number, author, diff, files changed
4. TrustScorer.compute(author, repo) → trust_profile
5. RiskAgent.compute(files, diff_size, trust_level) → risk_profile
6. ReviewerSuggester.suggest(repo, files, author) → reviewer
7. TriageAgent.analyze(diff, persona, trust, risk) → analysis [1 LLM call]
8. NemoClaw validates: schema check + forbidden action check
9. GitHubClient.create_check_run(repo, pr, analysis)
10. GitHubClient.post_pr_comment(repo, pr, formatted_comment)
11. GitHubClient.add_labels(repo, pr, [trust_label, risk_label])
12. Store PRAnalysis in DB
```

## Data Flow: /prclaw review

```
1. GitHub sends webhook: issue_comment.created
2. Comment body starts with "/prclaw review"
3. Fetch existing PRAnalysis from DB (already computed)
4. Fetch PR diff again for inline positioning
5. ReviewCommenter.generate(diff, persona, concerns) → inline_comments [1 LLM call]
6. NemoClaw validates: tone check + evidence check
7. GitHubClient.submit_pr_review(repo, pr, inline_comments, verdict)
```

## Data Flow: Issue Demand

```
1. GitHub sends webhook: issues.opened / issues.edited / issue_comment.created
2. IssueDemandAgent.score(issue) → demand_score [no LLM]
3. GitHubClient.add_label(repo, issue, demand_label)
4. If demand == "high": GitHubClient.post_issue_comment(demand_signal_comment)
5. Store IssueScore in DB
6. [Every 15 min background task]
   Fetch all open IssueScores with no cluster_id
   Batch embed titles+bodies → cluster [1 LLM call]
   Update cluster_id on each IssueScore
   Post cluster summary comment on the highest-demand issue in each cluster
```

---

## NemoClaw Integration

NemoClaw policy lives in `.github/prclaw.yml` in the target repo. The app fetches it on each event and applies it.

### Policy Enforcement Points

| Point | What's checked |
|---|---|
| Before posting any comment | `post_without_ai_disclosure` forbidden |
| Before applying label | Label allowed by policy |
| Before submitting review | Human `/prclaw review` command received |
| Before escalating | Risk + trust thresholds from policy |
| Trust scoring | Forbidden signals not used |
| Review comments | Tone + evidence requirements |

### Forbidden Actions (always blocked, no override)

```yaml
forbidden:
  - merge_pr
  - close_pr
  - close_issue
  - reject_contributor
  - post_without_ai_disclosure
  - use_identity_signals
```

---

## GitHub Output Surfaces

| Surface | When | Content |
|---|---|---|
| Check Run | PR open | Trust/Risk/Priority status, Details = full markdown report |
| PR Bot Comment | PR open | Trust badge, risk badge, summary, checklist, concerns, reviewer |
| PR Review (inline) | `/prclaw review` | Persona-voiced comments on specific lines |
| Issue Comment | High demand | Demand signal, days open, cluster links |
| Labels on PR | PR open | `trust:high/medium/new/flagged`, `risk:low/medium/high/critical` |
| Labels on Issue | Issue event | `demand:high/medium/low` |

---

## LLM Integration

Uses vLLM's OpenAI-compatible endpoint (`/v1/chat/completions`).

```python
# llm/client.py
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url=settings.VLLM_BASE_URL,
    api_key="not-needed"
)

async def call_llm(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    if settings.MOCK_MODE:
        return get_mock_response(prompt)
    
    response = await client.chat.completions.create(
        model=settings.VLLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.3
    )
    return response.choices[0].message.content
```

**Model:** `nvidia/Nemotron-Mini-4B-Instruct` or `nvidia/Nemotron-Nano-8B-Instruct` on Brev  
**Fallback:** `MOCK_MODE=true` for demo without GPU

---

## Token Budget

| Agent | Tokens In | Tokens Out | Frequency |
|---|---|---|---|
| Persona Extractor | ~4000 (50 reviews) | ~300 | Once/week |
| Triage | ~2000 (diff + context) | ~400 | Per PR |
| Review Commenter | ~2500 (diff + persona + concerns) | ~600 | Per `/prclaw review` |
| Issue Cluster | ~3000 (batch of issues) | ~500 | Every 15 min |

With prompt caching on repeated persona/system prompts: ~60-70% token reduction on Review Commenter calls.

---

## Security

- Webhook signature verification (HMAC SHA-256) on every incoming request
- GitHub App private key stored as file, never in env string
- JWT generation for GitHub App authentication (rotated every 10 min)
- Installation access tokens cached with expiry
- NemoClaw forbidden list enforced in code, not configurable away
- All bot comments include "AI-assisted" disclosure (policy-enforced)
