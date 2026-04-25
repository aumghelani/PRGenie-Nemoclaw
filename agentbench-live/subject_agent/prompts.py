"""Prompt templates structured for maximum prefix-cache hit rate.

Battle-plan §5A key trick:
    Put ALL tool definitions in the system message (not per-turn).
    Static instructions FIRST, dynamic content LAST.
    This maximizes the shared prefix across the 4 LLM calls in the loop.
"""
from __future__ import annotations

import json

from .tools import TOOL_SCHEMAS

# Long, static system prompt — repeated verbatim across every LLM call in
# the agent loop. With prefix caching ON this prefix is computed once and
# the KV blocks are reused for the rest of the loop (10x TTFT win).
SYSTEM_PROMPT = """You are AgentBench, a careful research agent. You answer
multi-part questions by decomposing them into sub-queries, calling tools to
gather evidence, synthesizing intermediate results, and producing a final
answer with citations.

## Operating principles
1. Decompose first, then act. Plan all sub-queries before invoking tools.
2. Prefer parallel tool calls when sub-queries are independent.
3. Keep tool-call arguments minimal — no chain-of-thought in arguments.
4. Cite every factual claim. Use [tool:name] markers in the final answer.
5. Respond immediately with function calls — do not reason extensively.

## Output discipline
- When calling tools, output ONLY the function call — no preamble text.
- When producing the final answer, return strict JSON matching the schema.
- max_tokens for tool calls is small (~150). Stay terse.

## Available tools
""" + json.dumps(TOOL_SCHEMAS, indent=2) + """

## Final-answer JSON schema
{
  "answer": "<concise final answer with [tool:X] citations>",
  "sub_findings": [{"question": "...", "finding": "...", "source": "..."}],
  "confidence": <float 0.0-1.0>
}
"""


def planner_prompt(user_query: str) -> str:
    """LLM Call 1 — decompose user query into 2-4 sub-queries."""
    return (
        "User query: " + user_query + "\n\n"
        "Step 1 (PLAN): Break this into 2-4 independent sub-queries that can be "
        "answered in parallel via tool calls. Return strict JSON: "
        '{"sub_queries": [{"id":"q1","question":"...","tools":["web_search"]}]} '
        "and nothing else."
    )


def synthesizer_prompt(user_query: str, tool_results: str) -> str:
    """LLM Call 2 — synthesize partial findings from parallel tool results."""
    return (
        "Original query: " + user_query + "\n\n"
        "Tool results (JSON): " + tool_results + "\n\n"
        "Step 2 (SYNTHESIZE): Combine these into 2-3 partial findings. "
        'Return JSON: {"findings": [{"point":"...","evidence":"..."}]}'
    )


def gap_finder_prompt(user_query: str, findings: str) -> str:
    """LLM Call 3 — identify gaps requiring follow-up tool calls."""
    return (
        "Original query: " + user_query + "\n\n"
        "Current findings: " + findings + "\n\n"
        "Step 3 (GAP CHECK): Which sub-queries still lack evidence? "
        "Issue at most 2 follow-up tool calls. If none needed, output "
        '{"follow_ups": []}.'
    )


def final_answer_prompt(user_query: str, findings: str) -> str:
    """LLM Call 4 — final structured answer (longest output, biggest spec-decode win)."""
    return (
        "Original query: " + user_query + "\n\n"
        "All findings: " + findings + "\n\n"
        "Step 4 (FINAL): Produce the final answer in the JSON schema from the "
        "system prompt. Be concise but cite every claim."
    )
