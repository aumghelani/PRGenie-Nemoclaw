"""Tool implementations for the Subject Agent.

For the hackathon demo we keep them deterministic / mocked so the agent
behaves identically across baseline and optimized runs — only the inference
stack changes between runs, which is what we want to measure.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
from typing import Any

# OpenAI-compatible tool schemas. Put these in the SYSTEM message so they
# become part of the prefix-cacheable prefix — this is the single biggest
# speedup lever (battle plan §5A).
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for recent information on a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "max_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "database_query",
            "description": "Look up structured records by key in the internal database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string"},
                    "key": {"type": "string"},
                },
                "required": ["table", "key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a numeric expression. Use for arithmetic only.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarizer",
            "description": "Summarize a text passage to <= max_words.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "max_words": {"type": "integer", "default": 80},
                },
                "required": ["text"],
            },
        },
    },
]


# --------------------------------------------------------------------------
# Deterministic mock implementations
# --------------------------------------------------------------------------

_MOCK_LATENCIES = {
    "web_search": (0.30, 0.60),
    "database_query": (0.05, 0.15),
    "calculator": (0.001, 0.005),
    "summarizer": (0.20, 0.40),
}


async def _simulate_latency(name: str) -> None:
    lo, hi = _MOCK_LATENCIES.get(name, (0.05, 0.15))
    rng = random.Random(hashlib.md5(name.encode()).digest())
    await asyncio.sleep(rng.uniform(lo, hi))


async def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    await _simulate_latency("web_search")
    return {
        "query": query,
        "results": [
            {"title": f"Result {i+1} for {query!r}", "snippet": f"Mocked snippet #{i+1}…"}
            for i in range(max_results)
        ],
    }


async def database_query(table: str, key: str) -> dict[str, Any]:
    await _simulate_latency("database_query")
    return {
        "table": table,
        "key": key,
        "record": {"value": f"record-{hashlib.md5(key.encode()).hexdigest()[:8]}"},
    }


async def calculator(expression: str) -> dict[str, Any]:
    await _simulate_latency("calculator")
    try:
        # Safe-ish: digits, ops, parens only.
        allowed = set("0123456789+-*/(). ")
        if not set(expression) <= allowed:
            raise ValueError("disallowed chars")
        return {"expression": expression, "result": eval(expression, {"__builtins__": {}}, {})}
    except Exception as e:
        return {"expression": expression, "error": str(e)}


async def summarizer(text: str, max_words: int = 80) -> dict[str, Any]:
    await _simulate_latency("summarizer")
    words = text.split()
    return {"summary": " ".join(words[:max_words])}


TOOL_IMPLS = {
    "web_search": web_search,
    "database_query": database_query,
    "calculator": calculator,
    "summarizer": summarizer,
}


async def dispatch(name: str, arguments: str | dict[str, Any]) -> str:
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}
    fn = TOOL_IMPLS.get(name)
    if fn is None:
        return json.dumps({"error": f"unknown tool {name}"})
    out = await fn(**arguments)
    return json.dumps(out)
