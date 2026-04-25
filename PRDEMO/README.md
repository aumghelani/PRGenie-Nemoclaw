# PRClaw

> **A GitHub-native AI agent that triages PRs, scores contributor trust, and surfaces high-demand issues — entirely inside GitHub.**
> Powered by **NemoClaw** policy enforcement + **vLLM**-served Nemotron.

---

## What is PRClaw?

PRClaw is a **GitHub App**. You install it on a repo, and it starts watching pull requests and issues like a hospital ER watches incoming patients — every PR is "intake," every issue is "a complaint at the front desk."

A team of **7 specialised agents** each plays a role:

| Hospital Role         | PRClaw Agent          | What it does in one line                                       |
|-----------------------|-----------------------|-----------------------------------------------------------------|
| Receptionist          | Trust Scorer          | Looks at the contributor's history — friend or stranger?        |
| Triage Nurse          | Risk Agent            | "How sick is this PR?" — diff size + sensitive files            |
| Lead Doctor           | Triage Agent          | Reads the chart, writes the diagnosis (summary + checklist)     |
| Specialist Referrer   | Reviewer Suggester    | Routes the case to the right specialist (file owner)            |
| Patient Profiler      | Persona Extractor     | Learns *how this maintainer* prefers to treat patients          |
| Senior Consultant     | Review Commenter      | Writes the formal opinion when the doctor says `/prclaw review` |
| Public Health Officer | Issue Demand Agent    | Watches the waiting room — flags outbreaks                      |

The whole hospital runs under one set of safety rules — `.github/prclaw.yml` — enforced by **NemoClaw** (the hospital's safety/compliance officer). No agent can do anything the policy file forbids.

---

## Quick start (mock mode, no GPU needed)

```bash
cd PRDEMO
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
cp .env.example .env            # MOCK_MODE=true is the default
uvicorn backend.main:app --reload --port 8080
```

Then:
```bash
curl http://localhost:8080/health
# → {"status": "ok", "service": "prclaw"}
```

---

## Architecture at a glance

```
GitHub  ──webhook──►  FastAPI /webhook
                          │
                          ▼
                  webhook_handler.py  (HMAC verified)
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   PR opened       /prclaw review      Issue opened
        │                 │                 │
        ▼                 ▼                 ▼
   ┌─Pipeline─┐    ReviewCommenter    IssueDemandAgent
   │ Trust    │    (1 LLM call)       (no LLM)
   │ Risk     │                              │
   │ Reviewer │                              ▼
   │ Triage   │ (1 LLM)              Label + comment
   └────┬─────┘                       (cluster every 15 min)
        ▼
  Check Run + bot comment + labels
        │
        ▼
       SQLite (cached)
```

Everything routes through the **NemoClaw policy enforcer** before any side-effect (label, comment, review).

---

## The 7 Agents (hospital-ER style)

Each card uses the same five-section template:
1. **Role** — what the agent does, one paragraph
2. **What it can access** — its inputs and read permissions
3. **What it's blocked from** — NemoClaw guardrails it cannot violate
4. **Policy snippet** — the `.github/prclaw.yml` keys that steer it
5. **How it talks to other agents** — its outputs and the shared "patient chart" (DB + GitHub API)

---

### 1. Trust Scorer — *the Receptionist*

**Role.**
First contact. When a PR lands, the Trust Scorer pulls up the contributor's record at this repo — past PRs, merge rate, how fast they answered review comments, account age — and stamps a coloured wristband on them: `high`, `medium`, `new`, or `flagged`. **Zero LLM calls** — pure rules. The receptionist doesn't diagnose; she identifies you.

**What it can access.**
- `GET /repos/{owner}/{repo}/pulls?creator={login}&state=all` (last 20 PRs)
- `GET /users/{login}` (account age only)
- DB cache: `ContributorTrust` row (re-uses if updated within `cache_hours`)

**What it's blocked from.**
- `use_identity_signals` — name, org, nationality, profile photo. Behaviour-only.
- Cannot label a contributor `flagged` based on anything outside the repo's own history.

**Policy snippet** (`.github/prclaw.yml`):
```yaml
trust:
  auto_label: true
  high_threshold: 0.75
  cache_hours: 24
```

**How it talks to other agents.**
Writes `ContributorTrust { trust_level, trust_score, signals }` to the DB. The Risk Agent reads `trust_level` to amplify risk. The Triage Agent reads the full record to colour its summary.

---

### 2. Risk Agent — *the Triage Nurse*

**Role.**
Looks at the wound, not the patient. Counts how many sensitive files the diff touches (`auth/`, `crypto/`, `requirements.txt`, `.github/workflows/`…), looks at the diff size, mixes in the contributor's trust band, and assigns a colour: `low / medium / high / critical`. **No LLM** — pattern matching on file paths.

**What it can access.**
- `pull_request.files` from the webhook payload
- `additions` / `deletions` counts
- `trust_level` from Trust Scorer (already in DB)
- `policy["risk"]["escalate_on"]` from the YAML

**What it's blocked from.**
- Cannot trigger an automatic close, merge, or reject — only labels and an escalation flag.
- Escalation only fires when **risk ≥ high AND trust ∈ {new, flagged}** — never just on diff size.

**Policy snippet:**
```yaml
risk:
  auto_label: true
  escalate_on:
    - auth/
    - crypto/
    - requirements.txt
    - .github/workflows/
```

**How it talks to other agents.**
Returns `{ risk_level, risk_score, sensitive_files, should_escalate }` in-process to the pipeline. The Triage Agent embeds this in its prompt; the GitHub client emits a `risk:*` label.

---

### 3. Triage Agent — *the Lead Doctor*

**Role.**
The only agent that holds the whole chart. Takes the diff, the maintainer's persona, the trust band, the risk profile, and writes the diagnosis: a 2–3 sentence summary, a priority, a list of concerns, and a reviewer checklist. **One LLM call per PR** — the most expensive call in the system.

**What it can access.**
- Full PR diff (truncated to 3000 chars: head 1500 + tail 1500)
- Maintainer persona JSON
- Trust + Risk profiles
- Suggested reviewer login

**What it's blocked from.**
- Output is schema-validated **before** posting. Free-form text outside the JSON schema is dropped.
- Cannot recommend `merge` or `close` actions — only `approve / request_changes / comment / escalate`.
- Cannot leak persona phrases as if they were the maintainer speaking — the comment is signed "🤖 PRClaw."

**Policy snippet** (steers tone & strictness via persona block):
```yaml
persona:
  focus: [correctness, tests, error_handling]
  strictness: 0.8
  tone: constructive but direct
```

**How it talks to other agents.**
Writes a full `PRAnalysis` row. The webhook handler calls `format_triage_comment(...)` and posts it to GitHub as a single bot comment + a Check Run. The Review Commenter (later, on `/prclaw review`) reads the cached `concerns` list to ground its inline comments.

---

### 4. Reviewer Suggester — *the Specialist Referrer*

**Role.**
Looks at every file the PR touches, asks GitHub "who has committed to this file most often?", sums up ownership across the changed files, and points at the most likely human reviewer. **No LLM** — straight `git blame` math via the commits API.

**What it can access.**
- `GET /repos/{owner}/{repo}/commits?path={file}` (last 30 per file, first 10 files)
- The PR author login (to *exclude* them)

**What it's blocked from.**
- Cannot suggest the PR author themselves.
- Cannot suggest reviewers with documented conflict threads with the author (NemoClaw-enforced when configured).
- Suggestion is a `@mention` only — the bot **never** assigns reviewers programmatically.

**Policy snippet:** governed by the global `forbidden` list — no dedicated knob.

**How it talks to other agents.**
Returns a single `login | None` to the pipeline. The Triage Agent embeds it in the bot comment as `**Suggested Reviewer:** @login`.

---

### 5. Persona Extractor — *the Patient Profiler*

**Role.**
Long-running anthropologist. Once a week (and on app install) it reads the maintainer's last 50 PR reviews and builds a JSON profile: what they care about, how strict they are, the phrases they keep using, what they tolerate. The other agents read this profile so the bot's voice matches the maintainer's. **One LLM call per week** — cached.

**What it can access.**
- `GET /repos/{owner}/{repo}/pulls/{n}/reviews` (last 50, across PRs)
- `MaintainerPersona` DB row (writes back the new profile)

**What it's blocked from.**
- No personal/identity inference — only **behavioural** signals from review text.
- Cannot infer beyond the public review record (no email scraping, no profile photo).

**Policy snippet:** the `persona` block seeds defaults when no review history exists yet.

**How it talks to other agents.**
Writes `MaintainerPersona { focus, strictness, tone, common_phrases, tolerance }`. The Triage Agent injects `focus`/`tone`/`strictness` into its prompt. The Review Commenter injects `common_phrases` to mimic voice.

---

### 6. Review Commenter — *the Senior Consultant*

**Role.**
Sleeps until the maintainer types `/prclaw review` on a PR. Then takes the cached triage concerns + the persona + the diff, and produces *inline review comments* positioned on specific lines, written in the maintainer's voice. **One LLM call per `/prclaw review` invocation.**

**What it can access.**
- Cached `PRAnalysis` (from the original PR-opened pipeline)
- Cached `MaintainerPersona`
- The PR diff again (for line-position lookup)

**What it's blocked from.**
- **Will not run without the human `/prclaw review` command.** The webhook handler asks NemoClaw `can_submit_review(triggered_by_command=True)` and bails if `False`.
- Each generated comment is run through `validate_review_comment()` — empty bodies and harsh-language patterns are dropped.
- Verdict can only be `COMMENT` or `REQUEST_CHANGES`; **never `APPROVE`**.

**Policy snippet:**
```yaml
forbidden:
  - merge_pr
  - close_pr
  - post_without_ai_disclosure
```

**How it talks to other agents.**
Calls `github.submit_pr_review(...)` directly with the comments + verdict. Writes nothing back to the DB — the review itself lives on GitHub.

---

### 7. Issue Demand Agent — *the Public Health Officer*

**Role.**
Watches the waiting room. Every issue event (open, comment, reaction) gets a fresh **demand score** = community engagement × age × maintainer silence. Labels each issue `demand:high/medium/low`. Every 15 minutes it batches all unclustered issues into one LLM call to group them by theme — so the maintainer sees "*9 issues are really one Redis bug*" instead of 9 noisy threads.

**What it can access.**
- `GET /repos/{owner}/{repo}/issues?state=open`
- `GET /repos/{owner}/{repo}/issues/{n}/reactions`
- `GET /repos/{owner}/{repo}/issues/{n}/comments`

**What it's blocked from.**
- Trust-neutral: scoring **does not** look at who filed the issue, their reputation, or any identity signal.
- Cannot close issues (`close_issue` is in the global `forbidden` list).
- Cluster comments only post on the highest-demand issue per cluster — never spam every issue in the cluster.

**Policy snippet:**
```yaml
demand:
  auto_label: true
  comment_threshold: 25
  cluster_min_size: 3
  cluster_interval_minutes: 15
```

**How it talks to other agents.**
Writes `IssueScore { demand_level, priority_score, cluster_id }`. Calls `github.add_label(...)` and (above threshold) `github.post_issue_comment(...)`.

---

## NemoClaw — the hospital's safety officer

NemoClaw is the **only** entity the agents go through to touch GitHub. Every `add_label`, every `post_*_comment`, every `submit_pr_review` is gated by:

```python
if not policy.can_post_comment(): return
if not policy.can_apply_label(label): return
if policy.is_action_forbidden(action): raise NemoClawViolation(...)
```

The policy lives in **`.github/prclaw.yml`** of the target repo. PRClaw fetches it on every event, merges it over a `DEFAULT_POLICY`, and feeds the merged dict to `PolicyEnforcer`.

**Forbidden actions** are *hard-coded* — no YAML can re-enable them:
- `merge_pr`
- `close_pr`
- `close_issue`
- `reject_contributor`
- `post_without_ai_disclosure`
- `use_identity_signals`

---

## File map

```
PRDEMO/
├── backend/
│   ├── main.py                  FastAPI entrypoint
│   ├── config.py                Pydantic settings (.env)
│   ├── webhook_handler.py       Routes events → agents      [Phase 1]
│   ├── github_client.py         GitHub REST wrapper          [Phase 3]
│   ├── agents/
│   │   ├── trust_scorer.py                                   [Phase 5]
│   │   ├── risk_agent.py                                     [Phase 6]
│   │   ├── reviewer_suggester.py                             [Phase 8]
│   │   ├── persona_extractor.py                              [Phase 9]
│   │   ├── triage_agent.py                                   [Phase 10]
│   │   ├── review_commenter.py                               [Phase 12]
│   │   └── issue_demand_agent.py                             [Phase 13]
│   ├── nemo_claw/
│   │   ├── policy_enforcer.py                                [Phase 7]
│   │   └── schemas.py                                        [Phase 7]
│   ├── llm/
│   │   ├── client.py            vLLM OpenAI-compat client    [Phase 4]
│   │   ├── prompts.py           Prompt templates             [Phase 4]
│   │   └── mock_responses.py    Mock data for demo           [Phase 4]
│   ├── db/
│   │   ├── models.py            SQLModel tables              [Phase 2]
│   │   └── store.py             CRUD helpers                 [Phase 2]
│   └── routers/
│       ├── webhook.py           POST /webhook                [Phase 1]
│       └── health.py            GET /health                  [Phase 0 ✓]
├── .github/
│   └── prclaw.yml               Sample NemoClaw policy
├── tests/
│   ├── test_trust_scorer.py
│   ├── test_triage_agent.py
│   └── mock_payloads/
│       ├── pr_opened.json
│       └── issue_created.json
├── requirements.txt
├── .env.example
├── ARCHITECTURE.md
├── IMPLEMENTATION_PLAN.md
├── CLAUDE.md
└── README.md (this file)
```

---

## Build status

| Phase | Description                              | Status |
|-------|------------------------------------------|--------|
| 0     | Project scaffold + README                | ✅ done |
| 1     | Webhook receiver + HMAC verify           | ✅ done (9 tests) |
| 2     | DB models + store                        | ✅ done (10 tests) |
| 3     | GitHub client                            | ✅ done (20 tests) |
| 4     | LLM client + mock mode                   | ✅ done (15 tests) |
| 5     | Trust Scorer                             | ✅ done (10 tests) |
| 6     | Risk Agent                               | ✅ done (9 tests) |
| 7     | NemoClaw policy enforcer                 | ✅ done (15 tests) |
| 8     | Reviewer Suggester                       | ✅ done (5 tests) |
| 9     | Persona Extractor                        | ✅ done (5 tests) |
| 10    | Triage Agent                             | ✅ done (7 tests) |
| 11    | Wire PR pipeline end-to-end              | ✅ done (4 e2e tests) |
| 12    | Review Commenter + `/prclaw review`      | ✅ done (4 tests) |
| 13    | Issue Demand Agent                       | ✅ done (8 tests) |
| 14    | Mock demo polish                         | ⏳ next |
| 15    | Live GitHub App (if GPU available)       |        |

---

## Wiring up Brev (when GPU is live)

PRClaw talks to vLLM via the OpenAI Chat Completions API. The team's vLLM is served from the scripts in `agentbench-live/vllm_setup/` on a Brev GPU instance.

**1. Confirm the vLLM endpoint on Brev:**
```bash
# On the Brev instance
bash 99_baseline_only.sh         # baseline (prefix caching OFF) — for the demo "before"
# OR
bash 04_serve_optimized.sh       # optimized (prefix caching + FP8 KV) — for the demo "after"
```
Both serve `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` on port `5000` with `--served-model-name nemotron`.

**2. Get the public URL** (Brev tunnel or instance public IP).

**3. Update `PRDEMO/.env`:**
```bash
VLLM_BASE_URL=http://<brev-ip>:5000/v1
VLLM_MODEL=nemotron
ENABLE_NVEXT_HEADERS=true
MOCK_MODE=false
```

**4. Restart `uvicorn backend.main:app`.**

The LLM client uses **OpenAI tool calling** (vLLM is started with `--enable-auto-tool-choice --tool-call-parser qwen3_coder`), so Nemotron will return structured JSON via `submit_triage` / `submit_persona` / `submit_review` / `submit_clusters` instead of free-form prose.

**Track 5 nvext headers** are sent on every LLM call when `ENABLE_NVEXT_HEADERS=true`:

| Header | What it carries | Why |
|---|---|---|
| `x-nvext-priority` | `high / medium / low` | Triage + Review = high; Persona + Clusters = low |
| `x-nvext-predicted-osl` | int (predicted output tokens) | NAT scheduler pre-allocates KV cache |
| `x-nvext-latency-sensitive` | `1 / 0` | User-facing calls flagged sensitive |
| `x-nvext-request-class` | `agent.first / agent.final / agent.background / agent.batch` | NAT routing + scoring metric |

Same persona system prompt is reused across calls → **vLLM prefix caching wins ~340ms per call** on the optimized server.

---

## Hackathon context

- **Event:** Red Hat / NVIDIA vLLM Hackathon, April 25 2026
- **Track:** 5 — Agentic Edge powered by NemoClaw (NVIDIA GPU Prize)
- **Required hooks:** NemoClaw load-bearing, vLLM, agentic workflow, tool calling
- **Pitch:** "We don't just automate PR review — we replicate how *this specific maintainer* reviews, including their style, their expectations, and their trust in contributors. NemoClaw makes sure we never overstep."
