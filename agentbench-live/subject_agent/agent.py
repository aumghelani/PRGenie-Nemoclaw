"""SubjectAgent — 4-LLM-call research loop with 4-8 tool invocations.

The loop intentionally has:
    - A long, static system prompt (prefix-cache target)
    - 4 LLM calls that all reuse that prefix
    - Independent tool calls between calls 1 and 2 (parallelism target)
    - A long final answer (speculative-decoding target)
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import httpx
from openai import AsyncOpenAI

from .prompts import (
    SYSTEM_PROMPT,
    planner_prompt,
    synthesizer_prompt,
    gap_finder_prompt,
    final_answer_prompt,
)
from .telemetry import TelemetryCollector
from .tools import TOOL_SCHEMAS, dispatch


@dataclass
class AgentConfig:
    base_url: str = "http://localhost:5000/v1"
    api_key: str = "dummy"
    model: str = "nemotron"
    request_timeout_s: float = 120.0
    # NAT-style nvext headers (battle plan §5F). Set to None to disable.
    nvext_priority: str | None = None  # "high" | "medium" | "low"
    nvext_predicted_osl: int | None = None
    nvext_latency_sensitive: bool | None = None


class SubjectAgent:
    def __init__(self, config: AgentConfig, collector: TelemetryCollector) -> None:
        self.config = config
        self.collector = collector
        self._client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=httpx.Timeout(config.request_timeout_s, connect=10.0),
        )

    # ---------------------------------------------------------------- LLM call

    async def _llm_call(
        self,
        name: str,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 256,
        with_tools: bool = False,
        priority: str | None = None,
        predicted_osl: int | None = None,
    ) -> dict[str, Any]:
        extra_headers: dict[str, str] = {}
        # nvext headers — vLLM ignores unknown headers, so safe to send always.
        # When NAT middleware is wired up, these drive priority scheduling.
        if priority or self.config.nvext_priority:
            extra_headers["x-nvext-priority"] = priority or self.config.nvext_priority
        if predicted_osl or self.config.nvext_predicted_osl:
            extra_headers["x-nvext-predicted-osl"] = str(
                predicted_osl or self.config.nvext_predicted_osl
            )
        if self.config.nvext_latency_sensitive is not None:
            extra_headers["x-nvext-latency-sensitive"] = (
                "1" if self.config.nvext_latency_sensitive else "0"
            )

        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.0,  # deterministic for benchmarking
        }
        if with_tools:
            kwargs["tools"] = TOOL_SCHEMAS
            kwargs["tool_choice"] = "auto"

        with self.collector.span(name, "llm", model=self.config.model) as span:
            t_first_token = None

            # Stream so we can capture TTFT.
            stream = await self._client.chat.completions.create(
                **kwargs, stream=True, extra_headers=extra_headers or None
            )
            chunks: list[str] = []
            tool_calls: list[dict[str, Any]] = []
            usage = None
            async for chunk in stream:
                if t_first_token is None:
                    t_first_token = self.collector._now_ms()
                if not chunk.choices:
                    if getattr(chunk, "usage", None):
                        usage = chunk.usage
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    chunks.append(delta.content)
                if delta and getattr(delta, "tool_calls", None):
                    for tc in delta.tool_calls:
                        while len(tool_calls) <= tc.index:
                            tool_calls.append({"id": None, "name": None, "arguments": ""})
                        slot = tool_calls[tc.index]
                        if tc.id:
                            slot["id"] = tc.id
                        if tc.function and tc.function.name:
                            slot["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            slot["arguments"] += tc.function.arguments
                if getattr(chunk, "usage", None):
                    usage = chunk.usage

            content = "".join(chunks)
            ttft = (
                t_first_token - span.start_ms if t_first_token is not None else None
            )
            self.collector.annotate(
                ttft_ms=ttft,
                input_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
                output_tokens=getattr(usage, "completion_tokens", None) if usage else None,
                tool_calls=len(tool_calls),
            )
            return {"content": content, "tool_calls": tool_calls}

    # ---------------------------------------------------------------- tool exec

    async def _run_tool(self, name: str, arguments: str | dict[str, Any]) -> str:
        with self.collector.span(f"tool:{name}", "tool", tool=name):
            return await dispatch(name, arguments)

    # ---------------------------------------------------------------- main loop

    async def run(self, user_query: str) -> dict[str, Any]:
        with self.collector.span("agent.run", "agent", query=user_query):

            # Call 1 — PLAN (small output, high priority for first-activity)
            plan = await self._llm_call(
                "llm.plan",
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": planner_prompt(user_query)},
                ],
                max_tokens=300,
                priority="high",
                predicted_osl=200,
            )

            sub_queries = _safe_json_load(plan["content"]).get("sub_queries", [])

            # Tool round 1 — fan out in parallel (this is the parallelism win)
            tool_tasks = []
            for sq in sub_queries[:4]:
                # Heuristic: route to web_search by default, db_query for "lookup"
                tool_name = "database_query" if "lookup" in sq.get("question", "").lower() else "web_search"
                args = (
                    {"table": "knowledge", "key": sq["question"]}
                    if tool_name == "database_query"
                    else {"query": sq.get("question", ""), "max_results": 3}
                )
                tool_tasks.append(self._run_tool(tool_name, args))
            tool_results = await asyncio.gather(*tool_tasks) if tool_tasks else []

            # Call 2 — SYNTHESIZE
            synth = await self._llm_call(
                "llm.synthesize",
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": synthesizer_prompt(
                            user_query, json.dumps(tool_results)[:4000]
                        ),
                    },
                ],
                max_tokens=400,
                predicted_osl=300,
            )

            # Call 3 — GAP CHECK with tool calling enabled (model decides
            # whether to issue follow-ups; follow-ups run sequentially after).
            gaps = await self._llm_call(
                "llm.gap_check",
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": gap_finder_prompt(user_query, synth["content"]),
                    },
                ],
                max_tokens=300,
                with_tools=True,
                predicted_osl=200,
            )

            followup_results: list[str] = []
            if gaps["tool_calls"]:
                followup_tasks = [
                    self._run_tool(tc["name"], tc["arguments"])
                    for tc in gaps["tool_calls"]
                    if tc["name"]
                ]
                followup_results = await asyncio.gather(*followup_tasks)

            findings_text = (
                synth["content"]
                + "\n\nFollow-ups: "
                + json.dumps(followup_results)[:2000]
            )

            # Call 4 — FINAL (longest output, biggest spec-decode win, last-call priority)
            final = await self._llm_call(
                "llm.final",
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": final_answer_prompt(user_query, findings_text),
                    },
                ],
                max_tokens=600,
                priority="high",
                predicted_osl=500,
            )

            return {
                "query": user_query,
                "answer": final["content"],
                "trace": self.collector.to_trace(),
            }


def _safe_json_load(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction — models sometimes wrap in code fences."""
    text = text.strip()
    if text.startswith("```"):
        # Strip ```json\n ... \n```
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[: -3]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last resort: empty plan
        return {}


async def run_task(query: str, config: AgentConfig, mode: str = "baseline") -> dict[str, Any]:
    collector = TelemetryCollector(mode=mode)
    agent = SubjectAgent(config, collector)
    return await agent.run(query)
