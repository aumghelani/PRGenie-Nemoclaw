# PRGenie — Pitch Deck

> 6 slides. Paste each into Google Slides / Keynote / PowerPoint as a separate page.

---

## SLIDE 1 — The Problem

# What if every PR came pre-reviewed… by you?

AI is **massively increasing contributions** to open source.
More PRs. More issues. More activity.

But maintainers haven't scaled.

**The problem isn't contribution.**
It's that there's only one of you.

> Backlog. Slower decisions. Burnout.

---

## SLIDE 2 — The Solution

# PRGenie — your maintainer twin

We replicate **how you make decisions on PRs** — fast, at scale.

| Existing tools (Greptile, CodeRabbit) | PRGenie |
|---|---|
| RAG over codebase | Learns *your behavior* — what you approve, reject, ask for |
| Generic "did this break?" | Persona-aware judgment calls |
| One-shot LLM per PR | Multi-agent pipeline, NemoClaw-steered |

> Powered by **NVIDIA NemoClaw** + **vLLM-served Nemotron / Llama** on NVIDIA NIM
> Track 5 — Agentic Edge powered by NemoClaw

---

## SLIDE 3 — Multi-agent architecture

# 5 specialised agents, each one job

| Agent | Role | Cost |
|---|---|---|
| **Trust Scorer** | Reads contributor's history → `high / medium / new / flagged` | No LLM (rules) |
| **Risk Agent** | Sensitive paths × diff size × trust → risk badge | No LLM (rules) |
| **Persona Extractor** | Learns your voice from your past reviews | 1 LLM call / week (cached) |
| **Triage Agent** | Reads diff + persona + risk → summary, concerns, checklist | 1 LLM call per PR |
| **Review Commenter** | Posts inline review in your voice on `/prgenie review` | 1 LLM call (human-triggered) |

**NemoClaw policy enforcer** sits in front of every action — steers and constrains output, blocks 9 hard-forbidden actions (`merge_pr`, `close_pr`, `use_identity_signals`, …).

---

## SLIDE 4 — The scoring math (behavior-only, no identity signals)

```python
# Contributor trust (no LLM, pure rules)
trust_score = 0.40 × merge_rate          # merged_prs / total_prs in this repo
            + 0.30 × response_score       # min(1.0, 24 / avg_response_hours)
            + 0.20 × resolution_rate      # resolved_changes / requested_changes
            + 0.10 × age_score            # min(1.0, account_age_days / 365)

# PR risk (no LLM, pattern matching)
base_risk   = +0.4 if any sensitive path touched (auth/, crypto/, requirements.txt, …)
            + 0.2 if diff > 500 lines      (+0.2 more if > 1000)
            + 0.3 if contributor is "new"  (+0.5 if "flagged")

# Issue demand (no LLM)
demand_score    = reactions × 0.4 + commenters × 0.3 + age × 0.2 + label_weight × 0.1
priority_score  = demand_score × max(1.0, days_since_maintainer_response / 7)
```

> Trust is **behavior-only**. NemoClaw forbids name / org / nationality / photo signals.

---

## SLIDE 5 — Why it's fast (the inference-efficiency story)

# 4× fewer calls. 4× fewer tokens. 4-5× faster.

| | Naive baseline | **PRGenie** |
|---|---|---|
| LLM calls per PR | 4 separate prompts | **1 tool-calling call** |
| Tokens per PR | ~3800 | **~960** |
| Latency per PR | ~42 s | **~9 s** |

**How:**
- **OpenAI tool-calling** — one structured JSON response replaces 4 prose-parsing rounds
- **vLLM prefix caching** — same `SYSTEM_*` prompts across all calls → cache hits
- **nvext steering headers** (`x-nvext-priority`, `predicted-osl`, `request-class`) — NAT scheduler routes Triage as `agent.first/high`, Persona as `agent.background/low`

> *Live measured numbers shown in the dashboard chart during demo.*

---

## SLIDE 6 — Demo + What you see

# For every PR, before you even open it:

✅ **Contributor trust** badge — `🟢 high` / `🟡 medium` / `⚪ new` / `🔴 flagged`
✅ **Risk** badge — `low / medium / high / critical`
✅ **Suggested reviewer** — from git-blame ownership math
✅ **Maintainer-voiced summary** — in your tone, citing your phrases
✅ **Concerns + review checklist** — specific, evidence-backed
✅ **Real GitHub comment posted** — every action passes NemoClaw policy gate first

> **Live demo:** PRGenie dashboard → enter any PR → 7 agent cards animate → real Llama call → real comment lands on real GitHub PR.

> **Track 5 win:** NemoClaw isn't a theme — it's *load-bearing* on every inference call and every side-effect.
