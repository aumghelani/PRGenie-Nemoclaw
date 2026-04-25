"""
LLM client wrapping the vLLM OpenAI-compatible Chat Completions endpoint.

Two modes (controlled by settings.MOCK_MODE):

  MOCK_MODE = True   → No network. complete_tool() returns the entry from
                       backend.llm.mock_responses.MOCK_BY_TOOL keyed on
                       the requested tool name. Used for tests + the
                       "demo without GPU" path.

  MOCK_MODE = False  → Real call to settings.VLLM_BASE_URL, model
                       settings.VLLM_MODEL ("nemotron"). Uses OpenAI tool
                       calling — vLLM is started with
                       `--enable-auto-tool-choice --tool-call-parser qwen3_coder`,
                       so Nemotron will emit a structured tool_call which we
                       parse into a Python dict.

Track 5 steerability:
  Every request includes nvext headers when settings.ENABLE_NVEXT_HEADERS
  is true. The headers are read by NAT middleware on the GPU host and used
  by vLLM scheduling for prioritization, predicted output length (OSL), and
  latency-class hints. See agentbench-live/nat_middleware/headers.py.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
from openai import AsyncOpenAI

from backend.config import settings
from backend.llm.mock_responses import MOCK_BY_TOOL

log = logging.getLogger("prclaw.llm")


# ---------------------------------------------------------------------------
# Steerability headers — Track 5 scoring requirement.
# ---------------------------------------------------------------------------

# Hand-picked OSL predictions per call type. Real OSL Prediction (the NAT
# crystal ball) would learn these from history; we seed reasonable defaults.
DEFAULT_OSL_TOKENS = {
    "submit_triage": 400,
    "submit_persona": 300,
    "submit_review": 600,
    "submit_clusters": 500,
}

# request_class strings the NAT middleware understands.
REQUEST_CLASS = {
    "submit_triage": "agent.first",     # PR-opened pipeline kicks off here
    "submit_persona": "agent.background",  # weekly refresh, low urgency
    "submit_review": "agent.final",     # human-triggered, high urgency
    "submit_clusters": "agent.batch",   # scheduled batch, low urgency
}


def build_nvext_headers(tool_name: str, *, latency_sensitive: bool | None = None) -> dict[str, str]:
    """Return the nvext headers for a given tool. Empty dict if disabled."""
    if not settings.ENABLE_NVEXT_HEADERS:
        return {}
    osl = DEFAULT_OSL_TOKENS.get(tool_name, 500)
    cls = REQUEST_CLASS.get(tool_name, "agent.default")
    if latency_sensitive is None:
        # Triage and review are user-visible → latency-sensitive.
        latency_sensitive = tool_name in ("submit_triage", "submit_review")
    priority = {"agent.first": "high", "agent.final": "high"}.get(cls, "medium")
    if cls in ("agent.background", "agent.batch"):
        priority = "low"
    return {
        "x-nvext-priority": priority,
        "x-nvext-predicted-osl": str(osl),
        "x-nvext-latency-sensitive": "1" if latency_sensitive else "0",
        "x-nvext-request-class": cls,
    }


# ---------------------------------------------------------------------------
# LLMClient
# ---------------------------------------------------------------------------


@dataclass
class RecordedLLMCall:
    """Captured call for tests / mock-mode demo log + dashboard metrics."""
    system: str
    user: str
    tool_name: str
    headers: dict
    response: dict
    latency_ms: float | None = None
    tokens: int | None = None


class LLMClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        mock_mode: bool | None = None,
    ):
        self.base_url = base_url if base_url is not None else settings.VLLM_BASE_URL
        self.model = model if model is not None else settings.VLLM_MODEL
        if mock_mode is None:
            mock_mode = settings.LLM_MOCK_MODE if settings.LLM_MOCK_MODE is not None else settings.MOCK_MODE
        self.mock_mode = mock_mode
        # vLLM ignores the key; NVIDIA cloud at integrate.api.nvidia.com requires an NGC key.
        self._client = AsyncOpenAI(base_url=self.base_url, api_key=settings.VLLM_API_KEY)
        self.recorded_calls: list[RecordedLLMCall] = []

    # ------------------------------------------------------------------

    async def complete_tool(
        self,
        *,
        system: str,
        user: str,
        tool: dict,
        latency_sensitive: bool | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict:
        """
        Call the LLM and force it to invoke `tool`. Returns the parsed
        JSON arguments dict. Raises ValueError if the model didn't call
        the tool or the JSON is malformed.
        """
        tool_name = tool["function"]["name"]
        headers = build_nvext_headers(tool_name, latency_sensitive=latency_sensitive)

        if self.mock_mode:
            response = MOCK_BY_TOOL.get(tool_name)
            if response is None:
                raise KeyError(f"No mock response for tool {tool_name!r}")
            self.recorded_calls.append(RecordedLLMCall(
                system=system, user=user, tool_name=tool_name, headers=headers, response=response,
                latency_ms=12.0,  # mock — instant
                tokens=len(json.dumps(response)) // 4,
            ))
            log.info("[mock-llm] tool=%s headers=%s", tool_name, headers)
            return response

        # Real call.
        t0 = time.perf_counter()
        try:
            completion = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                tools=[tool],
                tool_choice={"type": "function", "function": {"name": tool_name}},
                max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
                temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
                extra_headers=headers,
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as e:
            raise RuntimeError(f"vLLM call failed: {e}") from e

        msg = completion.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            raise ValueError(f"Model did not call {tool_name!r}. Got content: {msg.content!r}")

        call = tool_calls[0]
        try:
            args = json.loads(call.function.arguments)
        except json.JSONDecodeError as e:
            raise ValueError(f"Model returned malformed JSON for {tool_name!r}: {e}") from e

        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        usage = getattr(completion, "usage", None)
        tokens = getattr(usage, "total_tokens", None) if usage else None

        self.recorded_calls.append(RecordedLLMCall(
            system=system, user=user, tool_name=tool_name, headers=headers, response=args,
            latency_ms=latency_ms, tokens=tokens,
        ))
        log.info("llm tool_call name=%s latency_ms=%.1f tokens=%s", tool_name, latency_ms, tokens)
        return args


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def reset_llm_client() -> None:
    """For tests."""
    global _client
    _client = None
