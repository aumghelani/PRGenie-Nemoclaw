"""
Starter-Tier Template — Vibe-code your agent UI with Cursor
============================================================

This is an intentionally minimal scaffold. Open it in Cursor (or Claude Code,
or Copilot) and describe the UI you want — the AI will fill in the rest.

Good prompts to try:
  - "add a Gradio chat UI that streams tokens"
  - "make it answer questions about my PDF handbook"
  - "turn this into a research assistant that summarizes arXiv papers"

What's wired up for you:
  * vLLM chat client (OpenAI-compatible) pointing at your Brev instance
  * Single tool registered (knowledge_base_search)
  * Basic one-shot agent loop — no multi-turn, no memory

The Builder tier (customer_support_agent.py) extends this to a full multi-turn
agent with 4 tools. Use it as a reference when you're ready to level up.
"""

import os
import httpx

from tools import knowledge_base


VLLM_ENDPOINT = os.getenv("VLLM_ENDPOINT", "http://host.openshell.internal:8000/v1")
MODEL = os.getenv("MODEL", "/models/llama-3.1-8b-instruct")


def ask(question: str) -> str:
    """Minimal one-shot: retrieve, then answer."""
    hits = knowledge_base.search(question)
    context = "\n\n".join(f"[{h['id']}] {h['title']}: {h['content']}" for h in hits)

    r = httpx.post(
        f"{VLLM_ENDPOINT}/chat/completions",
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content":
                    "You are a helpful assistant. Use the KB snippets below to answer. "
                    "Cite the KB id in brackets after each fact."},
                {"role": "user", "content":
                    f"KB:\n{context}\n\nQuestion: {question}"},
            ],
            "temperature": 0.3,
            "max_tokens": 512,
        },
        timeout=60,
    )
    return r.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    # TODO (vibe-code with Cursor): replace this with a Gradio / Streamlit UI.
    while True:
        try:
            q = input("\nAsk: ").strip()
            if not q:
                break
            print(ask(q))
        except (EOFError, KeyboardInterrupt):
            break
