# Track Alignment Review — Official Hackathon Site vs. Repo

Reviewed against the official hackathon page at `OpenAccelerator/TOAsite/hackathon/upcoming/vLLM_LLM-D/index.html` (local copy).

Official event meta:
- **Date:** April 25, 2026, Fortpoint, Boston
- **Format:** 6 challenge tracks × 3 skill lanes (Starter / Builder / Deep Tech); ~3.5 h of core hack time
- **Prep:** Python 3.11+, **Podman** (not Docker), `pip install vllm`, GPU drivers
- **Judging:** 20 points across 5 criteria (Innovation 5, Execution 5, Inference Efficiency 4, Presentation 3, **Open-Source Contribution 3**)
- **Prizes:** Grand Prize (Red Hat), **Track 5 NVIDIA GPU Prize (RTX 5090)**, Most Promising Startup, People's Choice, **Best Upstream Contribution**

---

## Track-by-track alignment

Legend: ✅ covered · ⚠️ partial · ❌ missing

### Track 1 — The Lean Inference Challenge

Official tools: **LLM Compressor · GuideLLM · lm-eval-harness · Red Hat AI Models**

| Lane | Official ask | Repo status |
|------|--------------|-------------|
| Starter | Use **pre-quantized Red Hat AI model** from HF, benchmark with GuideLLM | ⚠️ `projects/beginner-shrink-to-fit/` uses generic AWQ HF models, not RedHatAI org |
| Builder | Quantize 7B–14B yourself with LLM Compressor | ✅ `projects/intermediate-compress-and-compare/` (GPTQ + AWQ) |
| Deep Tech | **FP8 / MXFP4** + speculative decoding compound gains | ❌ no FP8/MXFP4 examples; no compound-gain harness |

**Gaps:**
1. No RedHatAI-specific starter (the event sponsors want their models showcased)
2. No FP8 quantization example (LLM Compressor supports this out of the box)
3. No MXFP4 example (newer format, vLLM 0.8+)
4. No "compound gains" script that layers quantization + speculative decoding

**Fix:** added `projects/track1-redhat-fp8/` — Red Hat pre-quantized FP8 baseline + MXFP4 + compound-gain harness.

### Track 2 — RAG on Open Inference

Official tools: **vLLM · LangChain · LlamaIndex · ChromaDB · RAGAs**

| Lane | Official ask | Repo status |
|------|--------------|-------------|
| Starter | LangChain **or LlamaIndex** → ChromaDB → vLLM Q&A | ⚠️ `projects/beginner-ask-my-docs/` is LangChain-only |
| Builder | **Multimodal RAG** with vision-language models + **RAGAs** metrics + **reranking** + **hybrid search** | ❌ none of these |
| Deep Tech | **Prefix-cache-aware** query routing to minimize KV-cache misses | ❌ |

**Gaps:**
1. No LlamaIndex example (official page lists it as a first-class option)
2. No RAGAs evaluation (this is how Builder-lane teams are evaluated on the ask)
3. No reranker example (BGE reranker is the standard)
4. No multimodal RAG (Llama 3.2 Vision or NVLM-D)
5. No prefix-cache-aware routing example

**Fix:** added `projects/track2-ragas-rerank/` — LlamaIndex + BGE reranker + RAGAs eval + a short section on prefix-cache routing.

### Track 3 — Speculative Futures

Official tools: **vLLM Spec Decoding · Speculators v0.3.0 · EAGLE · Medusa**

| Lane | Official ask | Repo status |
|------|--------------|-------------|
| Starter | Deploy vLLM with spec decoding, benchmark speedup | ✅ `projects/intermediate-speed-demon/` (uses 8B-draft-for-70B) |
| Builder | **Train a speculator** for specific use case; compare **EAGLE / Medusa / N-gram** | ❌ no training; no EAGLE/Medusa variants |
| Deep Tech | **Auto-tune speculation length** + **regression test framework** | ⚠️ `sweep_spec_tokens.py` covers sweep but not auto-tune or regression tests |

**Gaps:**
1. Uses vLLM's built-in draft-model speculation only — no [Speculators v0.3.0](https://github.com/IBM/speculators) (event explicitly lists it)
2. No EAGLE (Llama-3.1-8B-EAGLE weights exist on HF)
3. No Medusa head example
4. No N-gram speculation comparison
5. No speculator **training** example (Builder lane requires it)
6. No CI regression harness (Deep Tech lane)

**Fix:** added `projects/track3-speculators-zoo/` — side-by-side comparison of draft-model, EAGLE, Medusa, and N-gram spec; acceptance-rate meter; CI regression YAML template.

### Track 4 — Inference at Scale

Official tools: **llm-d · Kubernetes · Inference Gateway · Helm**

| Lane | Official ask | Repo status |
|------|--------------|-------------|
| Starter | Deploy vLLM behind **llm-d Inference Gateway** via Helm | ⚠️ `projects/advanced-infinite-scale/` deploys llm-d but doesn't prominently use "Inference Gateway" terminology |
| Builder | **Multi-model deployment** + intelligent routing + **autoscaling** + **A/B traffic split** | ⚠️ single-model + autoscaling present; no multi-model or A/B |
| Deep Tech | Prefill/decode disaggregation + **extend llm-d benchmark harness** | ✅ disaggregation covered in `launchable-configs/tier3-deep-tech/` |

**Gaps:**
1. ~~"Inference Gateway" is the terminology the event uses — repo should match~~ ✅ addressed
2. ~~No multi-model / A/B split example~~ ✅ addressed
3. No contribution back to llm-d's benchmark harness demonstrated (recommended as a submission angle — not pre-built)

**Fix:** added `projects/track4-inference-gateway/` — multi-model Helm values, A/B canary-split values, runtime weight-shift script, independent HPA policies per pool, and traffic observation helpers. Uses "Inference Gateway" terminology throughout.

### Track 5 — Agentic Edge powered by NemoClaw 🏆

Official tools: **NemoClaw (required) · vLLM · Agentic Workflows · Tool Calling · Cursor**

| Lane | Official ask | Repo status |
|------|--------------|-------------|
| Starter | Pre-built NemoClaw template, vibe-code UI in Cursor, business use case | ✅ `demo/nemoclaw-agent/starter-template.py` |
| Builder | Multi-turn agentic workflow, tool-calling vs. base model | ✅ `demo/nemoclaw-agent/customer_support_agent.py` |
| Deep Tech | Latency optimization + custom steering + benchmarks | ✅ `demo/nemoclaw-agent/benchmarks/latency-test.py` |

**Gaps:** none. This track is the best-covered track in the repo.

### Track 6 — Performance Tuning & Evaluation

Official tools: **GuideLLM · vLLM Benchmarks · Prometheus · lm-eval-harness · Profiling**

| Lane | Official ask | Repo status |
|------|--------------|-------------|
| Starter | Run GuideLLM, collect TTFT/TPS/throughput, visualize, compare configs | ❌ no dedicated starter — tools installed but no scripts |
| Builder | Automated eval pipeline + **Prometheus** + **dashboards** + optimal params per use case | ❌ |
| Deep Tech | Profile vLLM internals, CI regression framework, upstream contribution | ❌ |

**Gaps:** **Entire track is unserved.** Tools are installed but there's no on-ramp — attendees picking Track 6 start from zero.

**Fix:** added `projects/track6-perf-lab/` — GuideLLM scenarios (chat/code/summarize), Prometheus + Grafana docker-compose, profiling notebook, and a CI regression template.

---

## Cross-cutting repo issues

### Issue 1: Docker vs. Podman ✅ addressed

The event prep page says **Podman**, not Docker. Several of our setup scripts (`launchable-configs/tier4-nemoclaw/setup.sh`, `demo/nemoclaw-agent/setup.sh`) require Docker. NemoClaw's OpenShell runtime itself needs Docker — so this is a real incompatibility to flag.

**Fix:** added [`docs/PODMAN-NOTES.md`](PODMAN-NOTES.md) (full compatibility matrix: Podman works everywhere except Track 5 NemoClaw) + `scripts/container-runtime.sh` (runtime-detection shim) + improved NemoClaw setup error message that detects Podman-only machines and points at the compat matrix.

### Issue 2: Upstream Contribution prize is not highlighted ✅ addressed

The event has a dedicated **Best Upstream Contribution** prize, and Open-Source Contribution is 3/20 points. The repo doesn't point attendees at specific good-first-issue candidates in vLLM, llm-d, LLM Compressor, or Speculators.

**Fix:** added [`docs/UPSTREAM-CONTRIBUTION-GUIDE.md`](UPSTREAM-CONTRIBUTION-GUIDE.md) with a target-repo table, per-track PR angles, submission checklist, and instructions for using mentors to nominate near-complete PRs.

### Issue 3: "Inference Efficiency Impact" scoring

4 of 20 points. Every project should produce **before/after numbers**. Our Track 5 bench harness already does this; most other tracks don't have a consistent metrics format. Not blocking but worth standardizing if there's time.

### Issue 4: Podium-worthy features that aren't starter projects but should be noted

Looking at the repo, some ideas that would make strong Track/Prize submissions but aren't yet seeded:

- **"Open Source Day" PR target list** — specific issues in vLLM/llm-d/LLM Compressor the organizers would love to see solved (high-value for Best Upstream Contribution prize)
- **Cost model notebook** — show $/1M-tokens across quantization × speculation × batch size. This hits Innovation + Inference Efficiency simultaneously
- **Eval dashboard template** — a reusable Grafana dashboard JSON + Prometheus scrape config (would be a Track 6 submission in itself)

---

## New starter projects added

1. `projects/track1-redhat-fp8/` — FP8 + compound gains (Red Hat quantization showcase)
2. `projects/track2-ragas-rerank/` — LlamaIndex + BGE reranker + RAGAs evaluation
3. `projects/track3-speculators-zoo/` — EAGLE / Medusa / N-gram / draft-model comparison
4. `projects/track4-inference-gateway/` — multi-model + A/B canary + independent HPA
5. `projects/track6-perf-lab/` — GuideLLM scenarios + Prometheus + profiling

## Cross-cutting additions

- [`docs/PODMAN-NOTES.md`](PODMAN-NOTES.md) + `scripts/container-runtime.sh` (runtime shim)
- [`docs/UPSTREAM-CONTRIBUTION-GUIDE.md`](UPSTREAM-CONTRIBUTION-GUIDE.md) with per-track PR angles

## Still deferred (recommendation only)

- Cost model notebook ($/1M tokens across quantization × speculation × batch size) — flagged as a strong Innovation-points submission but not pre-built
- Renaming `projects/advanced-infinite-scale/` to use "Inference Gateway" terminology — new Track 4 kit already does this; existing advanced project stays as Deep-Tech-focused complement
- Pre-cached list of specific good-first-issue URLs — deliberately omitted; the upstream guide recommends freshening these the week of the event

## Suggested attendee-guide updates

Add these sentences:

1. **Prep callout:** "The event page lists Podman in prep; Brev instances ship with Docker (equivalent for our purposes). Track 4 NemoClaw requires Docker."
2. **Prize callout in tracks table:** "Remember: **Best Upstream Contribution** is a dedicated prize. Any starter project can become an upstream PR — see `docs/UPSTREAM-CONTRIBUTION-GUIDE.md`."
3. **Judging callout:** "Inference Efficiency Impact is 4/20 points. Include before/after numbers in your 1-pager."

## Sources

- Local copy of hackathon site: `TOAsite/hackathon/upcoming/vLLM_LLM-D/index.html`
- [Red Hat AI on Hugging Face](https://huggingface.co/RedHatAI)
- [LLM Compressor](https://github.com/vllm-project/llm-compressor)
- [GuideLLM](https://github.com/neuralmagic/guidellm)
- [Speculators v0.3.0 (IBM)](https://github.com/IBM/speculators)
- [RAGAs](https://docs.ragas.io/)
- [llm-d Inference Gateway](https://github.com/llm-d/llm-d-inference-scheduler)
