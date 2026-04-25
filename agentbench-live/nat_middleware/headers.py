"""nvext header builder — produces the priority/OSL/latency-sensitivity headers
that tell vLLM how to schedule a request.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NvExtHeaders:
    priority: str | None = None  # "high" | "medium" | "low"
    predicted_osl: int | None = None  # output sequence length prediction
    latency_sensitive: bool | None = None
    request_class: str | None = None  # e.g. "agent.first", "agent.intermediate", "agent.final"


def build_headers(h: NvExtHeaders) -> dict[str, str]:
    out: dict[str, str] = {}
    if h.priority:
        out["x-nvext-priority"] = h.priority
    if h.predicted_osl is not None:
        out["x-nvext-predicted-osl"] = str(h.predicted_osl)
    if h.latency_sensitive is not None:
        out["x-nvext-latency-sensitive"] = "1" if h.latency_sensitive else "0"
    if h.request_class:
        out["x-nvext-request-class"] = h.request_class
    return out


# --- canned profiles for the agent loop call sites -------------------------

def first_call_headers(predicted_osl: int = 200) -> NvExtHeaders:
    """First call in the chain — drives time-to-first-activity SLO."""
    return NvExtHeaders(
        priority="high",
        predicted_osl=predicted_osl,
        latency_sensitive=True,
        request_class="agent.first",
    )


def intermediate_headers(predicted_osl: int = 300) -> NvExtHeaders:
    """Middle calls — can be deprioritized when system is loaded."""
    return NvExtHeaders(
        priority="low",
        predicted_osl=predicted_osl,
        latency_sensitive=False,
        request_class="agent.intermediate",
    )


def final_call_headers(predicted_osl: int = 500) -> NvExtHeaders:
    """Final call — drives time-to-final-answer SLO; long output (spec-decode target)."""
    return NvExtHeaders(
        priority="high",
        predicted_osl=predicted_osl,
        latency_sensitive=True,
        request_class="agent.final",
    )
