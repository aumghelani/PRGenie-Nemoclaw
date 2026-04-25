"""
Customer Support Agent — NemoClaw + vLLM
=========================================

Multi-turn agentic workflow demonstrating tool-calling against a vLLM backend.
This is the Builder-tier reference implementation for Track 5 (NVIDIA GPU Prize).

The agent:
  1. Receives a user query
  2. Decides which tool(s) to call (knowledge base, order lookup, tickets)
  3. Calls them, feeds results back into the conversation
  4. Repeats until it can give a final answer OR escalates to a human

Run inside the NemoClaw sandbox:
    nemoclaw agentic-edge connect
    python3 /workspace/customer_support_agent.py
"""

import json
import os
import sys
import time
from typing import List, Dict, Any

import httpx

from tools import knowledge_base, orders, tickets, escalation


# --- Config ---
VLLM_ENDPOINT = os.getenv("VLLM_ENDPOINT", "http://host.openshell.internal:8000/v1")
MODEL = os.getenv("MODEL", "/models/llama-3.1-8b-instruct")
MAX_TURNS = 8


# --- Tool schemas (OpenAI function-calling format) ---
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "knowledge_base_search",
            "description": "Search the product knowledge base for how-to articles, policies, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural-language search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Look up a customer order by its ID (format: ORD-####).",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID e.g. ORD-1001"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Open a support ticket when the issue needs human follow-up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "description": {"type": "string"},
                    "customer_email": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                },
                "required": ["subject", "description", "customer_email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Transfer to a human agent. Use for refund approvals > $100 or frustrated customers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                    "customer_email": {"type": "string"},
                    "conversation_summary": {"type": "string"},
                },
                "required": ["reason", "customer_email", "conversation_summary"],
            },
        },
    },
]


# --- Tool dispatch ---
def execute_tool(name: str, args: Dict[str, Any]) -> str:
    """Run the named tool with arguments and return a JSON string result."""
    try:
        if name == "knowledge_base_search":
            result = knowledge_base.search(args["query"])
        elif name == "lookup_order":
            result = orders.lookup(args["order_id"])
            if result is None:
                result = {"error": f"Order {args['order_id']} not found"}
        elif name == "create_ticket":
            result = tickets.create(**args)
        elif name == "escalate_to_human":
            result = escalation.escalate(**args)
        else:
            result = {"error": f"Unknown tool: {name}"}
    except Exception as e:
        result = {"error": f"Tool execution failed: {e}"}
    return json.dumps(result)


# --- Chat loop ---
SYSTEM_PROMPT = """You are a customer support agent for an e-commerce company.

You have four tools available:
- knowledge_base_search: for policies, how-tos, general product info
- lookup_order: when the customer mentions an order ID
- create_ticket: when you can't resolve the issue but don't need a human immediately
- escalate_to_human: for refunds > $100, upset customers, or after 3 failed attempts

Rules:
- Call tools before answering — don't guess
- When you have enough info, give a clear, friendly answer
- Always cite order IDs and KB article IDs in your answer
- Be concise: < 120 words unless the customer needs detailed steps
"""


def run_agent(user_query: str, customer_email: str = "unknown@example.com") -> str:
    """Run the multi-turn agentic loop until a final answer is produced."""
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"[customer: {customer_email}] {user_query}"},
    ]

    for turn in range(MAX_TURNS):
        response = httpx.post(
            f"{VLLM_ENDPOINT}/chat/completions",
            json={
                "model": MODEL,
                "messages": messages,
                "tools": TOOL_SCHEMAS,
                "tool_choice": "auto",
                "temperature": 0.3,
                "max_tokens": 1024,
            },
            timeout=120,
        )
        response.raise_for_status()
        msg = response.json()["choices"][0]["message"]
        messages.append(msg)

        # No tool calls → we have a final answer.
        if not msg.get("tool_calls"):
            print(f"\n[agent] {msg['content']}")
            return msg["content"]

        # Execute each tool call and feed results back.
        for tc in msg["tool_calls"]:
            tool_name = tc["function"]["name"]
            tool_args = json.loads(tc["function"]["arguments"])
            print(f"[turn {turn+1}] calling {tool_name}({tool_args})")
            result = execute_tool(tool_name, tool_args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "name": tool_name,
                "content": result,
            })

    return "Agent hit max turns without a final answer."


# --- Demo ---
if __name__ == "__main__":
    test_cases = [
        ("alice@example.com", "Where is my order ORD-1001? It's been a while."),
        ("bob@example.com", "How do I reset my password?"),
        ("carol@example.com", "I want to return order ORD-1003 — the cables don't fit my laptop."),
        ("dave@example.com", "I need a $500 refund, I'm very upset!"),
    ]

    for email, query in test_cases:
        print("\n" + "=" * 70)
        print(f"Customer: {email}")
        print(f"Query: {query}")
        print("=" * 70)
        start = time.time()
        run_agent(query, email)
        print(f"[meta] Completed in {time.time() - start:.2f}s")
