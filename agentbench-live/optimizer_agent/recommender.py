"""Translates analyzer findings into vLLM config recommendations."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from .analyzer import TraceAnalyzer


@dataclass
class Recommendation:
    name: str
    expected_savings_ms: float
    vllm_flag: str | None  # CLI flag to add (or None for app-side change)
    rationale: str
    confidence: float  # 0.0 - 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Recommender:
    def __init__(self, analyzer: TraceAnalyzer) -> None:
        self.analyzer = analyzer

    def recommend(self) -> list[Recommendation]:
        recs: list[Recommendation] = []
        stats = self.analyzer.stats()

        # 1. Prefix caching — biggest single win when LLM calls share prefix.
        if stats.n_llm_calls >= 2 and stats.prefix_recompute_ms_estimate > 100:
            recs.append(
                Recommendation(
                    name="Enable prefix caching",
                    expected_savings_ms=stats.prefix_recompute_ms_estimate,
                    vllm_flag="--enable-prefix-caching",
                    rationale=(
                        f"{stats.n_llm_calls} LLM calls share the same system prompt "
                        f"+ tool definitions. Caching the KV blocks for that prefix "
                        f"saves ~250 ms/call on calls 2-{stats.n_llm_calls}, totaling "
                        f"~{stats.prefix_recompute_ms_estimate:.0f} ms."
                    ),
                    confidence=0.95,
                )
            )

        # 2. Parallel tool execution — if any sibling tool calls ran serially.
        for opp in stats.serial_tool_blocks:
            if opp.savings_ms > 30:
                recs.append(
                    Recommendation(
                        name=f"Parallelize {len(opp.span_ids)} tool calls",
                        expected_savings_ms=opp.savings_ms,
                        vllm_flag=None,  # app-side fix, not a vLLM flag
                        rationale=(
                            f"{len(opp.span_ids)} sibling tool calls ran serially "
                            f"({opp.total_serial_ms:.0f} ms) but have no data "
                            f"dependencies. Running with asyncio.gather drops to "
                            f"{opp.parallel_ms_estimate:.0f} ms (max of the set), "
                            f"saving {opp.savings_ms:.0f} ms."
                        ),
                        confidence=0.85,
                    )
                )

        # 3. Speculative decoding — biggest wins on the long final answer.
        if stats.n_llm_calls >= 1:
            recs.append(
                Recommendation(
                    name="Enable speculative decoding (EAGLE-3)",
                    expected_savings_ms=_estimate_spec_decode_savings(self.analyzer),
                    vllm_flag="--speculative-model RedHatAI/eagle3-... --num-speculative-tokens 5",
                    rationale=(
                        "Final-answer call generates the most tokens. EAGLE-3 "
                        "drafter typically achieves 1.5-1.7x decode speedup on "
                        "structured JSON output."
                    ),
                    confidence=0.70,
                )
            )

        # 4. FP8 KV cache — only if context is long-ish.
        if (stats.avg_ttft_ms or 0) > 200:
            recs.append(
                Recommendation(
                    name="Enable FP8 KV cache",
                    expected_savings_ms=0.0,  # not latency, but unlocks longer ctx
                    vllm_flag="--kv-cache-dtype fp8",
                    rationale=(
                        "Halves KV cache memory, doubling effective context length "
                        "with negligible quality loss. Frees memory for batching."
                    ),
                    confidence=0.80,
                )
            )

        # 5. Agentic headers — always recommended for multi-call loops.
        recs.append(
            Recommendation(
                name="Send nvext priority/OSL headers (NAT middleware)",
                expected_savings_ms=_estimate_agentic_headers_savings(stats),
                vllm_flag=None,
                rationale=(
                    "Tag the first and last LLM calls in the chain as high-priority "
                    "and intermediate calls as low-priority. Under concurrent load, "
                    "the meetup data shows -62% TTFT at medium utilization and -89% "
                    "TTFT at high utilization."
                ),
                confidence=0.65,
            )
        )

        # Sort by expected savings, descending.
        recs.sort(key=lambda r: r.expected_savings_ms, reverse=True)
        return recs

    def to_vllm_diff(self) -> dict[str, list[str]]:
        """Return the set of vLLM CLI flags to add."""
        flags = [r.vllm_flag for r in self.recommend() if r.vllm_flag]
        return {"add_flags": flags}


def _estimate_spec_decode_savings(analyzer: TraceAnalyzer) -> float:
    """Final-answer LLM call decode time × 0.4 (1.7x speedup → 41% saved)."""
    final_calls = [
        s for s in analyzer.spans if s["kind"] == "llm" and s["name"] == "llm.final"
    ]
    if not final_calls:
        return 0.0
    s = final_calls[0]
    decode_ms = max(0.0, s["duration_ms"] - (s["attrs"].get("ttft_ms") or 0))
    return decode_ms * 0.41


def _estimate_agentic_headers_savings(stats) -> float:
    """At medium load -62% TTFT × number of LLM calls × avg TTFT."""
    if not stats.avg_ttft_ms:
        return 0.0
    return stats.avg_ttft_ms * 0.62 * stats.n_llm_calls
