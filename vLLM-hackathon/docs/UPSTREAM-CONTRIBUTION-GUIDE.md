# Upstream Contribution Guide

The hackathon awards a dedicated **Best Upstream Contribution** prize to the work most likely to land as a merged PR in vLLM, llm-d, or related projects. Open-source contribution is also worth 3/20 judging points on every track.

This guide gives you concrete starting points: which repos to target, how to find actionable issues, and how to turn each track's starter kit into a shippable PR.

> ⚠️ Issue links go stale. Check each project's live `good first issue` / `help wanted` label at the event date — don't rely on specific issue numbers pre-cached here.

---

## Target repositories

| Project | Repo | Best label to filter | Typical PR size |
|---------|------|----------------------|-----------------|
| vLLM | [vllm-project/vllm](https://github.com/vllm-project/vllm/issues) | `good first issue`, `help wanted`, `feature request` | medium |
| llm-d core | [llm-d/llm-d](https://github.com/llm-d/llm-d/issues) | `good first issue`, `help wanted` | small-medium |
| Inference Scheduler | [llm-d/llm-d-inference-scheduler](https://github.com/llm-d/llm-d-inference-scheduler/issues) | `help wanted` | small |
| LLM Compressor | [vllm-project/llm-compressor](https://github.com/vllm-project/llm-compressor/issues) | `good first issue` | small |
| GuideLLM | [neuralmagic/guidellm](https://github.com/neuralmagic/guidellm/issues) | `help wanted` | small |
| Speculators v0.3.0 | [IBM/speculators](https://github.com/IBM/speculators/issues) | `help wanted` | small |
| NemoClaw | [NVIDIA/NemoClaw](https://github.com/NVIDIA/NemoClaw/issues) / [brevdev/NemoClaw](https://github.com/brevdev/NemoClaw/issues) | alpha — expect to file issues | small |
| lm-eval-harness | [EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness/issues) | `contributions welcome` | small-medium |

## How to find a good first issue (fast)

```bash
# Direct search URLs — drop these into your browser at the event
https://github.com/vllm-project/vllm/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22
https://github.com/llm-d/llm-d/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22
https://github.com/vllm-project/llm-compressor/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22
```

Or with `gh`:

```bash
gh issue list --repo vllm-project/vllm --label "good first issue" --state open --limit 20
gh issue list --repo llm-d/llm-d --label "help wanted" --state open --limit 20
```

## Turning each track into a PR

The starter kits in `projects/` are already designed with upstream-PR potential in mind. Here are the most-likely paths for each track:

### Track 1 — Lean Inference

- **New quantization scheme example** in `llm-compressor/examples/` — copy `projects/track1-redhat-fp8/quantize_mxfp4.py` into an examples directory with a README, open a PR.
- **Benchmark harness** — propose `projects/track1-redhat-fp8/benchmark_compound.py` as a reusable GitHub Action for vLLM's perf CI. Shows compound gains across versions.
- **Model card addition** on [RedHatAI](https://huggingface.co/RedHatAI) — if you quantize a model Red Hat hasn't yet published (e.g., a fresh 14B), open a contribution discussion on HF.

### Track 2 — RAG

- **LlamaIndex ↔ vLLM example** — the `LlamaIndex` docs have a vLLM integration page but are thin on reranking. Contribute a worked example based on `projects/track2-ragas-rerank/`.
- **RAGAs + vLLM recipe** — contribute a cookbook entry to [RAGAs docs](https://github.com/explodinggradients/ragas) that uses vLLM as both LLM and embedding backend.
- **Prefix-cache-aware retriever** — propose a `PrefixCacheAwarePostprocessor` to LlamaIndex that orders retrieved nodes to maximize prefix reuse.

### Track 3 — Speculators

- **New speculator type in vLLM** — if your Builder-lane submission trains an EAGLE head, upstream weights + a vLLM serving example.
- **Regression harness** — propose `projects/track3-speculators-zoo/regression/spec_regression_test.py` as a reusable GitHub Action for the vLLM project.
- **Speculators v0.3.x new model support** — the [Speculators](https://github.com/IBM/speculators) project welcomes support for additional target model architectures.

### Track 4 — Inference at Scale

- **llm-d Helm values example** — multi-model example from `projects/track4-inference-gateway/` is a direct contribution candidate to [`llm-d/charts/llm-d/examples/`](https://github.com/llm-d/llm-d).
- **Inference Scheduler routing strategy** — propose a new routing policy (sticky-by-session, round-robin-with-affinity) to [`llm-d/llm-d-inference-scheduler`](https://github.com/llm-d/llm-d-inference-scheduler).
- **Benchmark harness extension** — event page explicitly asks to "extend llm-d's benchmark harness with new metrics." Adding `prefix_cache_hit_ratio` or per-model p99 latency is high-value.

### Track 5 — NemoClaw

- **Bug reports / fixes** — NemoClaw is alpha. File reproducible issues at [NVIDIA/NemoClaw](https://github.com/NVIDIA/NemoClaw) or [brevdev/NemoClaw](https://github.com/brevdev/NemoClaw). Alpha-stage projects value bug reports highly.
- **vLLM integration example** — propose an official worked example of NemoClaw + vLLM to their docs.
- **Blueprint templates** — upstream useful `blueprint.yaml` patterns (customer support, research assistant) as NemoClaw templates.

### Track 6 — Performance Tuning & Evaluation

- **Grafana dashboard** — `projects/track6-perf-lab/grafana/vllm-dashboard.json` is a direct contribution to [vLLM's docs](https://github.com/vllm-project/vllm/tree/main/docs/source/serving). The project explicitly welcomes dashboard contributions.
- **Prometheus recording rules** — contribute `projects/track6-perf-lab/prometheus/alert-rules.yml` to the vLLM serving docs.
- **Regression CI template** — reusable GitHub Action that wraps `check_regression.py`. Frame as "catch vLLM perf regressions before they merge."
- **GuideLLM scenarios** — `projects/track6-perf-lab/scenarios/*.yaml` could become the canonical scenario set. Propose upstream to [GuideLLM](https://github.com/neuralmagic/guidellm).
- **Profiling recipe** — turn `profile_vllm.py` into a vLLM docs entry: "How to find hot paths in your vLLM deployment."

---

## PR submission checklist

Before your 4:30 PM deadline, make sure your PR (or proposed PR) has:

- [ ] **Clear title** — imperative, scoped, e.g. "Add MXFP4 quantization example to docs"
- [ ] **Before/after numbers** if it's a perf or quality change (judges weight "Inference Efficiency Impact" 4/20)
- [ ] **Tests** (or at least a reproducing command) if it's a bug fix
- [ ] **Signed commits** if the project uses DCO (vLLM and llm-d both require `--signoff`)
- [ ] **Linked GitHub issue** if one exists — get bonus points from the maintainer
- [ ] **Short demo video** (≤2 min) showing the change in action — the hackathon requires this anyway

## Submission framing for the Best Upstream Contribution prize

Your 1-page concept brief should explicitly call out:

1. **Target repo + issue number** (or "new feature — no prior issue")
2. **PR link** (draft is fine — maintainer review can happen post-event)
3. **Measurable impact** — don't just say "better"; say "+18% throughput on scenario X"
4. **Reviewer path** — tag the track's core committer mentor in your PR; they often review in real time during the hack

## Mentors can nominate

Core vLLM, llm-d, and related committers are mentoring on the day. If your PR is not quite ready by 4:30, a mentor nomination ("this team's PR is 90% there, here's the branch") still qualifies for the Upstream Contribution prize. Ask your mentor — early, not at 4:25.

## Links

- [vLLM contributing guide](https://docs.vllm.ai/en/latest/contributing/overview.html)
- [llm-d contributing guide](https://github.com/llm-d/llm-d/blob/main/CONTRIBUTING.md)
- [GuideLLM contributing](https://github.com/neuralmagic/guidellm/blob/main/CONTRIBUTING.md)
- [How to sign off commits (DCO)](https://wiki.linuxfoundation.org/dco)
