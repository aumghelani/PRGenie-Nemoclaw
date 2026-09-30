# PRGenie

A GitHub webhook service (FastAPI) that triages pull requests, scores contributor trust and PR risk, suggests reviewers and ranks issues by community demand, using NVIDIA Nemotron served through an OpenAI-compatible endpoint (vLLM or NVIDIA NIM).

![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-webhooks-teal) ![Tests](https://img.shields.io/badge/tests-126-brightgreen)

## Overview

PRGenie was built for the Red Hat / NVIDIA vLLM Hackathon (April 2026, Track 5: agentic edge). It is designed to run as a GitHub App: GitHub sends webhook events, and PRGenie responds with labels, a Check Run, a triage comment on each new PR, and inline review comments when a maintainer types `/prgenie review`.

The pipeline combines rule-based agents (no LLM) with a small number of structured LLM calls:

- **Rule-based**: contributor trust, PR risk, reviewer suggestion, issue demand scoring.
- **LLM (OpenAI tool calling)**: maintainer persona extraction, PR triage summary, inline review generation.

Every side effect passes through a policy layer (`backend/nemo_claw/`) configured per repository by `.github/prgenie.yml`. This policy layer is implemented inside the app; it is not the NVIDIA NemoClaw sandbox runtime.

A mock mode lets the webhook pipeline run end to end with no GPU, no LLM endpoint and no GitHub credentials.

## Key Features

- **Trust Scorer** (no LLM): scores a contributor from their last 20 PRs on the repo and account age, and assigns `trust:high|medium|new|flagged`. Uses behavior-only signals, never identity. Results are cached in SQLite (`cache_hours`, default 24).
- **Risk Agent** (no LLM): matches changed paths against sensitive patterns (`auth/`, `crypto/`, `requirements.txt`, `Dockerfile`, `.github/workflows/`, `migrations/`, plus repo-configured `escalate_on`), adds diff size and trust band, and assigns `risk:low|medium|high|critical` with a `should_escalate` flag (high/critical risk from a new or flagged contributor).
- **Reviewer Suggester** (no LLM): sums commit ownership over the first 10 changed files (last 30 commits each) and suggests the top non-author as an `@mention`. It never assigns reviewers.
- **Persona Extractor** (1 LLM call, cached 7 days): builds a maintainer profile (focus areas, strictness, tone, common phrases, tolerance) from their recent PR reviews.
- **Triage Agent** (1 LLM call per PR): produces a summary, priority, concerns, checklist and suggested action (`approve`, `request_changes`, `comment` or `escalate`) from the truncated diff, persona, trust and risk. Results are saved for later review commands.
- **Review Commenter** (1 LLM call, human-triggered only): on `/prgenie review`, generates inline comments grounded in the cached triage concerns. Comments with harsh language or empty/too-short bodies are dropped, and the verdict is limited to `COMMENT` or `REQUEST_CHANGES` (never `APPROVE`).
- **Issue Demand Agent** (no LLM): scores issues on reactions, comment count, age, label weight and maintainer silence, applies `demand:high|medium|low` labels, and comments on high-demand issues above a reaction threshold.
- **Policy enforcement**: per-repo YAML (validated with Pydantic and merged over defaults) controls auto-labeling, extra sensitive paths, trust cache duration and the demand comment threshold. Triage comments are checked for an AI-disclosure marker before posting. A hard-coded forbidden list (`merge_pr`, `close_pr`, `close_issue`, `reject_contributor`, `post_without_ai_disclosure`, `use_identity_signals`) cannot be removed by YAML, and the GitHub client has no merge or close methods.
- **Webhook security**: HMAC-SHA256 verification of `X-Hub-Signature-256` with a constant-time compare.
- **Inference steering headers**: optional `x-nvext-*` headers (priority, predicted output length, latency sensitivity, request class) on each LLM call, for schedulers that read them.
- **Demo surfaces**: a single-page web dashboard, a `triage-pr` CLI and a `repo-pulse` CLI for issue demand across a repository.

## Architecture

```
GitHub --webhook--> POST /webhook (HMAC verified) --> webhook_handler.route_event
                                                          |
         +------------------------------------------------+-------------------------+
         |                                                |                         |
   pull_request opened/                         issue_comment              issues opened/
   synchronize/reopened                         "/prgenie review"          edited/reopened
         |                                                |                         |
   PolicyEnforcer.from_repo                        Review Commenter          Issue Demand Agent
   Trust -> Risk -> Reviewer                       (1 LLM call, uses         (rule-based score)
   Persona (cached) -> Triage (1 LLM call)         cached triage)                   |
         |                                                |                   demand:* label
   disclosure check -> labels + Check Run          PR review with                     |
   + triage comment -> SQLite                      inline comments               SQLite
```

- **LLM client** (`backend/llm/client.py`): `AsyncOpenAI` pointed at `VLLM_BASE_URL`, forcing a specific tool (`submit_triage`, `submit_persona`, `submit_review`) so the model returns schema-shaped JSON. In mock mode it returns canned responses from `backend/llm/mock_responses.py`.
- **GitHub client** (`backend/github_client.py`): direct REST calls via `httpx`, authenticated with a personal access token or GitHub App installation tokens (RS256 JWT). In mock mode, reads return fixtures and writes are recorded instead of sent.
- **Storage**: SQLite via SQLModel with tables for maintainer personas, contributor trust, PR analyses and issue scores.

### Scoring formulas

```
trust_score  = merge_rate*0.40 + response_score*0.30 + resolution_rate*0.20 + age_score*0.10
               (no prior PRs -> "new"; >=0.75 high; >=0.45 medium; else flagged)

risk_score   = +0.4 sensitive path, +0.2 if diff > 500 lines, +0.2 more if > 1000,
               +0.3 if trust "new", +0.5 if trust "flagged"   (clamped to 1.0)
               (>=0.8 critical; >=0.5 high; >=0.25 medium; else low)

demand_score = reactions*0.4 + comments*0.3 + min(days_open/30, 1)*0.2 + label_weight*0.1
priority     = demand_score * max(1, days_since_maintainer_response / 7)
               (>=8 high; >=3 medium; else low)
```

## Tech Stack

Python 3.11+, FastAPI, Uvicorn, Pydantic v2, pydantic-settings, SQLModel, SQLite, httpx, OpenAI Python SDK (AsyncOpenAI), OpenAI tool calling, vLLM, NVIDIA Nemotron, NVIDIA NIM, GitHub REST API, GitHub Apps, GitHub Webhooks, PyJWT, cryptography, PyYAML, Click, Rich, pytest, pytest-asyncio, HTML, Tailwind CSS (CDN), Chart.js, marked.js

## Getting Started

### 1. Install

```bash
git clone https://github.com/aumghelani/PRGenie-Nemoclaw.git
cd PRGenie-Nemoclaw
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install "sqlmodel<0.0.45"
cp .env.example .env    # MOCK_MODE=true by default
```

The `sqlmodel<0.0.45` pin is required: `requirements.txt` is unpinned, and SQLModel 0.0.45 and later reject the naive datetimes this code stores, which breaks the database layer (27 of 126 tests fail).

### 2. Run the server in mock mode

```bash
uvicorn backend.main:app --port 8080
curl http://localhost:8080/health     # {"status":"ok","service":"prgenie"}
curl http://localhost:8080/api/info   # {"service":"prgenie","mock_mode":true,"model":"nemotron"}
```

### 3. Send a signed test webhook

The bundled payloads run the full pipeline offline against mocked GitHub and LLM clients. The secret must match `GITHUB_WEBHOOK_SECRET` in `.env` (`your_webhook_secret` in `.env.example`):

```bash
PAYLOAD=tests/mock_payloads/pr_opened.json
SIG=$(openssl dgst -sha256 -hmac your_webhook_secret < "$PAYLOAD" | awk '{print $2}')
curl -X POST http://localhost:8080/webhook \
  -H "X-GitHub-Event: pull_request" \
  -H "X-Hub-Signature-256: sha256=$SIG" \
  -H "Content-Type: application/json" \
  --data-binary @"$PAYLOAD"
```

The response reports trust level, risk level, priority, suggested reviewer and the (mock) labels, Check Run and comment that would be created. Use `issues` with `issue_created.json`, or `issue_comment` with `issue_comment_command.json` (a `/prgenie review` command; send it after the PR event so a cached analysis exists).

### 4. Dashboard and CLI against real PRs

The dashboard (`http://localhost:8080/`), `POST /api/triage` and the CLI always call the live GitHub API, even in mock mode, so they need a `GITHUB_PAT` in `.env`. The LLM stays mocked unless `MOCK_MODE=false` (or `LLM_MOCK_MODE=false`).

```bash
python -m backend.cli triage-pr owner/repo 42 --dry-run   # analyze without posting
python -m backend.cli triage-pr owner/repo 42             # posts the comment and labels
python -m backend.cli repo-pulse owner/repo --limit 30    # rank open issues by demand
```

### 5. Use a real model

Point `VLLM_BASE_URL` at any OpenAI-compatible server that supports tool calling and set `MOCK_MODE=false`. `scripts/brev_serve_*.sh` contain the `vllm serve` commands used for NVIDIA Nemotron-3-Nano-30B-A3B (BF16 and FP8, 2 GPUs, with `--enable-auto-tool-choice --tool-call-parser qwen3_coder`); `scripts/test_against_brev.sh` checks that an endpoint responds. For NVIDIA's hosted API, set `VLLM_BASE_URL=https://integrate.api.nvidia.com/v1`, `VLLM_API_KEY` and `ENABLE_NVEXT_HEADERS=false`.

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `MOCK_MODE` | `true` | Mock both GitHub and LLM clients |
| `GITHUB_MOCK_MODE` / `LLM_MOCK_MODE` | inherit `MOCK_MODE` | Override one side independently |
| `GITHUB_PAT` | empty | Personal access token; used instead of GitHub App auth when set |
| `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY_PATH` | empty, `./github-app.pem` | GitHub App authentication |
| `GITHUB_WEBHOOK_SECRET` | `dev_secret_change_me` | HMAC secret for `/webhook` |
| `VLLM_BASE_URL` | `http://localhost:5000/v1` | OpenAI-compatible endpoint |
| `VLLM_MODEL` | `nemotron` | Served model name |
| `VLLM_API_KEY` | `not-needed` | API key for hosted endpoints |
| `ENABLE_NVEXT_HEADERS` | `true` | Send `x-nvext-*` steering headers |
| `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS` | `0.3`, `1024`, `60` | LLM call settings |
| `DATABASE_URL` | `sqlite:///./prdemo.db` | SQLModel database URL |

### HTTP API

| Method and path | Purpose |
|---|---|
| `GET /` | Web dashboard |
| `GET /health` | Health check |
| `GET /api/info` | Service name, mock mode and model name |
| `POST /api/triage` | `{"repo": "owner/repo", "pr_number": 1, "dry_run": true}`; runs the PR pipeline and returns analysis and LLM call metrics (requires `GITHUB_PAT`) |
| `POST /webhook` | GitHub webhook receiver (HMAC verified) |

## Project Structure

```
backend/
  main.py               FastAPI app and lifespan (creates DB tables)
  config.py             pydantic-settings configuration (.env)
  webhook_handler.py    event routing and the PR / issue / review pipelines
  github_client.py      GitHub REST client with mock mode
  cli.py                triage-pr and repo-pulse commands
  agents/               trust, risk, reviewer, persona, triage, review, issue demand
  nemo_claw/            policy schema and PolicyEnforcer
  llm/                  OpenAI-compatible client, prompts and tool schemas, mock responses
  db/                   SQLModel tables, session, CRUD helpers
  routers/              /health, /webhook, dashboard and /api/triage
static/dashboard.html   single-page dashboard
.github/prgenie.yml     sample repository policy
scripts/                vLLM serve scripts and endpoint/sandbox probes
tests/                  pytest suite and sample webhook payloads
ARCHITECTURE.md, IMPLEMENTATION_PLAN.md, PITCH.md   design and hackathon notes
```

## Testing

```bash
pytest
```

The suite has 126 tests covering the webhook receiver, GitHub client, LLM client, policy enforcer, each agent, the DB layer and end-to-end pipeline runs. Tests use mock mode, `httpx.ASGITransport` and an in-memory SQLite database, so no network access is needed. All 126 pass with `sqlmodel<0.0.45`; with the latest SQLModel, 27 fail (see Getting Started).

## Limitations and Roadmap

- **Dependencies are unpinned**; the `sqlmodel<0.0.45` workaround above is needed until timestamps are made timezone-aware or versions are pinned.
- **Issue clustering is not scheduled**: `cluster_issues()` and its LLM prompt exist but nothing calls them.
- **Escalation notifies nobody**: `should_escalate` is computed and returned but does not trigger any mention or notification.
- **Partial trust signals**: review response time and change-request resolution use neutral placeholder values until review-thread data is fetched.
- **Many sample policy keys are not read**: only the `auto_label` flags, `trust.cache_hours`, `risk.escalate_on`, `demand.comment_threshold` and `forbidden` change behavior. The `review`, `escalation`, `persona`, trust `weights`/thresholds and `label_weights` sections in `.github/prgenie.yml` are ignored or display-only; scoring weights and thresholds are hard-coded.
- **Issue events**: only `opened`, `edited` and `reopened` issue events are scored; reactions and new comments do not trigger rescoring. Submitted PR reviews are logged but not used to refresh personas.
- **Dashboard comparison chart**: the "naive" baseline is an estimate derived from the current run (4x calls, +15% latency, 4x tokens), not a separate measured run.
- **Dashboard rendering**: the LLM-generated triage comment is rendered with `marked.parse` into `innerHTML` without sanitization, a minor XSS risk if model output is untrusted.
- **Maintainer identity**: in webhook mode the repository owner is used as the maintainer whose persona is learned.
