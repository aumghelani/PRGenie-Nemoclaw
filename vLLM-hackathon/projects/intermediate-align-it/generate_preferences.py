"""
Align It — Generate preference pairs from the base model.

Samples the base model at two different temperatures for each prompt:
  - Low temperature (0.2): focused, predictable, often higher quality
  - High temperature (1.2): creative but sometimes rambling or off-topic

For each pair, uses a simple heuristic to label "chosen" and "rejected"
(length, formatting, coherence signals). You can also edit the output
to manually override labels.

In a real pipeline you'd use human annotators or a stronger model as judge.

Usage:
    python3 generate_preferences.py
    python3 generate_preferences.py --num-pairs 100 --port 8000
"""

import argparse
import json
import os
import time

import httpx

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "preference_data.jsonl")

PROMPTS = [
    "Explain the concept of dependency injection and when you would use it.",
    "Write a Python class that implements a simple pub/sub event system.",
    "What are the best practices for writing good error messages in software?",
    "Describe how garbage collection works in Python.",
    "Write a clear, well-structured code review comment for a function that has too many parameters.",
    "Explain the difference between authentication and authorization with examples.",
    "What should I consider when designing a REST API for a new service?",
    "Write a Python function that implements exponential backoff for retrying API calls.",
    "Explain what a race condition is and how to prevent one in Python.",
    "Describe the SOLID principles and give a brief example of each.",
    "Write a Python context manager that times code execution and logs the result.",
    "What are the trade-offs between SQL and NoSQL databases?",
    "Explain how HTTPS works at a high level, including the role of certificates.",
    "Write a Python function that validates and normalizes phone numbers.",
    "What are some common anti-patterns in Python and how do you fix them?",
    "Explain the Observer pattern with a practical example.",
    "Write a clear docstring for a complex function that processes user data.",
    "What are the key differences between threads and processes in Python?",
    "Describe how you would debug a memory leak in a Python web application.",
    "Write a Python generator that yields Fibonacci numbers.",
    "Explain what eventual consistency means and where it applies.",
    "What makes a good commit message? Give examples of good and bad ones.",
    "Write a Python function that safely merges two dictionaries with conflict resolution.",
    "Explain the concept of immutability and why it matters in concurrent programming.",
    "Describe how you would design a rate limiter for an API endpoint.",
]


def generate_response(url: str, model: str, prompt: str, temperature: float) -> str:
    """Generate a response from vLLM."""
    r = httpx.post(
        f"{url}/chat/completions",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful, knowledgeable assistant. Give clear, well-structured answers."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 512,
            "temperature": temperature,
        },
        timeout=90,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def heuristic_label(response_a: str, response_b: str) -> tuple[str, str]:
    """
    Simple heuristic to pick which response is better.

    Prefers responses that are:
    - Not too short (shows effort) but not excessively long (rambling)
    - Well-structured (contains paragraphs or bullet points)
    - Doesn't repeat itself

    Returns (chosen, rejected).
    """
    def score(text: str) -> float:
        s = 0.0
        # Reasonable length (not too short, not too long)
        word_count = len(text.split())
        if 50 < word_count < 400:
            s += 2.0
        elif word_count < 20:
            s -= 2.0

        # Has structure (bullet points, numbered lists, paragraphs)
        if any(text.count(c) >= 2 for c in ["\n-", "\n*", "\n1."]):
            s += 1.0

        # Has code blocks (if relevant)
        if "```" in text:
            s += 0.5

        # Penalize excessive repetition
        sentences = text.split(".")
        unique_ratio = len(set(sentences)) / max(len(sentences), 1)
        if unique_ratio < 0.7:
            s -= 1.5

        return s

    score_a = score(response_a)
    score_b = score(response_b)

    if score_a >= score_b:
        return response_a, response_b
    else:
        return response_b, response_a


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", default="/models/llama-3.1-8b-instruct")
    parser.add_argument("--num-pairs", type=int, default=50)
    args = parser.parse_args()

    url = f"http://localhost:{args.port}/v1"

    print("=" * 55)
    print("  Align It — Generating Preference Data")
    print(f"  Model: {args.model}")
    print(f"  Pairs to generate: {args.num_pairs}")
    print(f"  Output: {OUTPUT_FILE}")
    print("=" * 55)

    records = []
    for i in range(args.num_pairs):
        prompt = PROMPTS[i % len(PROMPTS)]

        # Generate two responses at different temperatures
        resp_low = generate_response(url, args.model, prompt, temperature=0.2)
        resp_high = generate_response(url, args.model, prompt, temperature=1.2)

        chosen, rejected = heuristic_label(resp_low, resp_high)

        record = {
            "prompt": prompt,
            "chosen": chosen,
            "rejected": rejected,
        }
        records.append(record)

        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{args.num_pairs}] generated")

    # Write JSONL
    with open(OUTPUT_FILE, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    print(f"\nGenerated {len(records)} preference pairs")
    print(f"Saved to: {OUTPUT_FILE}")
    print("\nNext: python3 train_dpo.py")


if __name__ == "__main__":
    main()
