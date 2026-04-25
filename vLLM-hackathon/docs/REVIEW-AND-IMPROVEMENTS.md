# Repository Review & Improvement Proposal

> 📎 **Historical document.** This was the first review pass, done before the full official hackathon page HTML was available. For the current, source-of-truth gap analysis — which incorporates the canonical track descriptions and records what's been addressed since — see [TRACK-ALIGNMENT-REVIEW.md](TRACK-ALIGNMENT-REVIEW.md).
>
> Keeping this file for context: it explains the rationale behind the Track 5 NemoClaw addition and the initial Brev/Launchable deployment recommendations.

This document reviews the state of the hackathon repo at the point of Track 5's introduction, compares it with the public [TOA vLLM / LLM-D Hackathon page](https://the-open-accelerator.com/hackathon/upcoming/vLLM_LLM-D/), proposes improvements using **NVIDIA Brev** and **Launchables**, and introduces **Track 5 — NVIDIA GPU Prize: Agentic Edge powered by NemoClaw**.

> ⚠️ The public hackathon page returned a 403 during automated inspection at the time of this writing. Comparison below was based on the tracks already documented in the attendee guide plus the user-provided Track 5 description. The subsequent [TRACK-ALIGNMENT-REVIEW.md](TRACK-ALIGNMENT-REVIEW.md) pass validated everything against the actual HTML.

---

## 1. Current repo state

The repo covers six tracks across three Brev Launchable tiers:

| Track | Name | Tier | Materials in repo |
|------:|------|------|-------------------|
| 1 | Lean Inference Challenge (quantization) | Tier 2 | `benchmarks/quantize_model.py`, `bench_throughput.sh` |
| 2 | RAG on Open Inference | Tier 1 | LangChain + ChromaDB + BGE in tier1 setup |
| 3 | Speculative Futures | Tier 2 | `speculative_decoding.sh` (8B draft, 70B target) |
| 4 | Inference at Scale (llm-d on K8s) | Tier 3 | llm-d Helm values + kind cluster scripts |
| 5 | BYOP — Build Your Own Product | Tier 1 | FastAPI scaffold at `/workspace/app-scaffold/` |
| 6 | Performance Tuning & Evaluation | Any | guidellm + lm-eval installed, no dedicated scripts |

Additionally, the repo now ships:
- A **ZeroClaw code-assistant demo** (`demo/`) showing quantized local LLMs + cloud fallback
- Cost estimator spreadsheet
- An attendee guide

## 2. What's good

- **Three-tier Brev Launchable strategy** maps cleanly to skill level and GPU budget
- **Pre-cached model weights** in each setup.sh — attendees don't burn hack time waiting on downloads
- **Starter scripts per track** (quantization, speculative decoding, llm-d deployment) — lowers the onboarding friction from hours to minutes
- **OpenAI-compatible endpoint** across the board — attendees can use the tooling they already know

## 3. Gaps & recommendations

### 3.1 Missing: NVIDIA-specific track and hardware story

The current repo is vendor-neutral. Since the hackathon is hosted at a venue expecting NVIDIA sponsorship and a GPU prize, adding a **dedicated NVIDIA track** is important:

- **Addressed:** New **Track 5 — Agentic Edge powered by NemoClaw** (see `demo/nemoclaw-agent/` and `launchable-configs/tier4-nemoclaw/`)
- NemoClaw is NVIDIA's sandbox stack for autonomous agents, built to integrate directly with vLLM via the OpenAI-compatible `/v1/chat/completions` protocol
- The new Tier-4 Launchable runs on a single A100/H100 — cheaper to provision than Tiers 2/3 — so NVIDIA can sponsor more teams per dollar

### 3.2 Improve: Launchable creation and distribution

The current `BREV_CONFIG.md` files document manual console steps. Several improvements:

1. **Add Launchable badges to README.** Brev supports one-click launch badges you can embed in GitHub:
   ```markdown
   [![Launch](https://brev.nvidia.com/badge.svg)](https://brev.nvidia.com/launchable/deploy?launchableID=<id>)
   ```
   Reference: [One-click deployments blog](https://developer.nvidia.com/blog/one-click-deployments-for-the-best-of-nvidia-ai-with-nvidia-launchables/)

2. **Publish Launchables with "Link Sharing" visibility** (not "Organization") so attendees can click through without being added to the org. Covered in [Brev Launchables docs](https://docs.nvidia.com/brev/concepts/launchables).

3. **Provide a `brev port-forward` cheat sheet** in the attendee guide for direct API access without browser Cloudflare auth, useful for `curl` / benchmarking scripts. See [Brev console reference](https://docs.nvidia.com/brev/latest/guides/console-reference).

### 3.3 Improve: Cost and sizing

- **Tier 4 (NemoClaw) sits at 1× A100 80GB** — deliberately cheaper than Tier 2/3 because the agent loop is more about orchestration than raw throughput
- **Add a "bring-your-own-GPU" option** for attendees with RTX 5090 / 4090 laptops via a laptop-mode entry in the attendee guide (already seeded in `demo/` via Ollama path)
- The Brev [team feature](https://docs.nvidia.com/brev/latest/guides/console-reference) lets the organizers share one team org with mentors and sponsors — consider provisioning a shared pool rather than per-team credits

### 3.4 Improve: Tier 4 as the NVIDIA showcase

The `launchable-configs/tier4-nemoclaw/` Launchable includes:

- **vLLM with `--enable-auto-tool-choice --tool-call-parser hermes`** — this is the key flag set most blog posts miss; without it, tool calls come back as text blobs rather than structured `tool_calls`
- **NemoClaw onboarded non-interactively** via env-var flags so attendees can rerun `setup.sh` without TUI interaction
- **Four inference profiles** in `blueprint.yaml` (vllm, vllm-steered, nim-local, nvidia-cloud) — attendees can switch with one command: `openshell inference set --provider <name>`
- **Latency benchmark harness** so teams can quantify Deep Tech submissions

### 3.5 Improve: Evaluation story for Track 6

Track 6 (Performance Tuning & Evaluation) currently doesn't ship dedicated scripts. Suggested additions:

- A `benchmarks/` directory at the repo root with standard workloads (ShareGPT, hellaswag, MMLU)
- A `eval_compare.py` that runs lm-eval against two model variants side-by-side and outputs a diff table
- Pre-written GuideLLM scenarios (`chat`, `code`, `summarize`) so teams can compare apples-to-apples

Flagging this as future work rather than adding it here.

---

## 4. Using Brev + Launchables to run the hackathon

### 4.1 Recommended sequence for organizers

1. **Fork this repo** to the organizer's GitHub account
2. **Create four Brev Launchables** — one per tier — using the `BREV_CONFIG.md` in each `launchable-configs/tier*/` directory
3. For each Launchable:
   - Set **Code Source → Git** pointing at the forked repo — this way attendees get the whole repo inside `/workspace` automatically
   - Paste the tier's `setup.sh` into the **Environment Setup** step
   - Enable **Cloudflare tunnels** on ports 8000 (vLLM), 8080 (app scaffold), 7860 (Gradio)
   - Set **Visibility → Link Sharing** and **Name → `toa-hackathon-<tier>`**
4. **Embed the launch badges** in the README (one per tier) so attendees pick their track from GitHub directly
5. **Pre-warm** one instance of each Launchable the day before — first-run model downloads take 10–30 minutes and you want the image cache hot

### 4.2 What the attendee experience looks like

```
Attendee opens repo on GitHub
    ↓
Clicks "Deploy to Brev" badge for their chosen tier
    ↓
Brev provisions GPU (1–2 min) + runs setup.sh (10–30 min first time, ~30s cached)
    ↓
Attendee clicks "Open Jupyter" or SSH'd via their IDE (Cursor, VS Code Remote)
    ↓
Starts hacking — vLLM server already running, models pre-downloaded, tools installed
```

### 4.3 NemoClaw Track 5 — end-to-end flow

```
Deploy tier4-nemoclaw Launchable
    ↓
bash /workspace/start_vllm_server.sh      (vLLM up on :8000)
bash /workspace/onboard_nemoclaw.sh       (NemoClaw wired to local vLLM)
    ↓
Starter:   python3 /workspace/starter-template.py          ← vibe-code in Cursor
Builder:   python3 /workspace/customer_support_agent.py    ← multi-turn reference
Deep Tech: python3 /workspace/benchmarks/latency-test.py   ← profile comparison
```

---

## 5. New Track 5 deliverable summary

| Piece | Location |
|-------|----------|
| Track description | `demo/nemoclaw-agent/README.md` |
| Starter scaffold | `demo/nemoclaw-agent/starter-template.py` |
| Builder reference agent | `demo/nemoclaw-agent/customer_support_agent.py` |
| Tools (KB, orders, tickets, escalation) | `demo/nemoclaw-agent/tools/` |
| NemoClaw blueprint | `demo/nemoclaw-agent/blueprint.yaml` |
| Deep Tech benchmarks | `demo/nemoclaw-agent/benchmarks/latency-test.py` |
| Brev Launchable config | `launchable-configs/tier4-nemoclaw/` |

Attendees get: a working Starter scaffold, a full multi-turn reference, four inference profiles to compare, and a benchmark harness with pre-defined difficulty tiers.

## Sources

- [The Open Accelerator hackathon hub](https://the-open-accelerator.com/)
- [NVIDIA Brev console reference](https://docs.nvidia.com/brev/latest/guides/console-reference)
- [Brev Launchables concept docs](https://docs.nvidia.com/brev/concepts/launchables)
- [One-click deployments blog](https://developer.nvidia.com/blog/one-click-deployments-for-the-best-of-nvidia-ai-with-nvidia-launchables/)
- [NemoClaw (NVIDIA)](https://github.com/NVIDIA/NemoClaw)
- [NemoClaw (brevdev)](https://github.com/brevdev/NemoClaw)
- [NemoClaw local inference guide](https://docs.nvidia.com/nemoclaw/latest/inference/use-local-inference.html)
- [NemoClaw inference profiles](https://docs.nvidia.com/nemoclaw/0.0.1/reference/inference-profiles.html)
- [NVIDIA tech blog — secure local AI agent with NemoClaw](https://developer.nvidia.com/blog/build-a-secure-always-on-local-ai-agent-with-nvidia-nemoclaw-and-openclaw/)
