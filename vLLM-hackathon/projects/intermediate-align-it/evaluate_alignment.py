"""
Align It — Evaluate alignment before and after DPO training.

Sends the same prompts to both the base and aligned models, then:
  1. Shows side-by-side comparisons
  2. Calculates automated quality signals (structure, length, repetition)
  3. Reports an estimated win rate for the aligned model

Prerequisites:
    bash serve_aligned.sh  (base on 8000, aligned on 8001)

Usage:
    python3 evaluate_alignment.py
"""

import json
import os
import statistics

import httpx

BASE_URL = "http://localhost:8000/v1/chat/completions"
ALIGNED_URL = "http://localhost:8001/v1/chat/completions"
BASE_MODEL = "/models/llama-3.1-8b-instruct"
ALIGNED_MODEL = "aligned"  # LoRA adapter name

EVAL_PROMPTS = [
    "Explain what a database transaction is and why ACID properties matter.",
    "Write a Python function that implements a thread-safe singleton pattern.",
    "What are the key considerations when designing a caching strategy?",
    "Explain the concept of backpressure in streaming systems.",
    "Write a clear, helpful error message for when a user's session has expired.",
    "What are the main differences between gRPC and REST?",
    "Describe how you would implement pagination for a large dataset API.",
    "Explain what container orchestration is and why Kubernetes is popular.",
    "Write a Python function that validates JSON against a schema.",
    "What are the best practices for logging in production applications?",
]


def generate(url: str, model: str, prompt: str) -> str:
    """Generate a response from a model."""
    r = httpx.post(url, json={
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful, knowledgeable assistant."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 512,
        "temperature": 0.3,
    }, timeout=90)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def quality_score(text: str) -> float:
    """Heuristic quality score for a response."""
    score = 0.0
    words = text.split()
    word_count = len(words)

    # Reasonable length
    if 50 < word_count < 400:
        score += 2.0
    elif word_count < 20:
        score -= 2.0
    elif word_count > 500:
        score -= 1.0

    # Structure (bullet points, numbered lists, headers)
    if any(text.count(c) >= 2 for c in ["\n- ", "\n* ", "\n1."]):
        score += 1.5
    if "```" in text:
        score += 1.0

    # Penalize repetition
    sentences = [s.strip() for s in text.split(".") if s.strip()]
    if sentences:
        unique_ratio = len(set(sentences)) / len(sentences)
        if unique_ratio < 0.7:
            score -= 2.0

    # Penalize excessive filler
    filler_phrases = ["in conclusion", "it's worth noting", "it is important to note"]
    for filler in filler_phrases:
        if filler.lower() in text.lower():
            score -= 0.5

    return score


def main():
    print("=" * 60)
    print("  Align It — Alignment Evaluation")
    print(f"  Prompts: {len(EVAL_PROMPTS)}")
    print("=" * 60)

    wins_aligned = 0
    wins_base = 0
    ties = 0
    details = []

    for i, prompt in enumerate(EVAL_PROMPTS):
        print(f"\n[{i+1}/{len(EVAL_PROMPTS)}] {prompt[:60]}...")

        base_response = generate(BASE_URL, BASE_MODEL, prompt)
        aligned_response = generate(ALIGNED_URL, ALIGNED_MODEL, prompt)

        base_score = quality_score(base_response)
        aligned_score = quality_score(aligned_response)

        if aligned_score > base_score:
            winner = "aligned"
            wins_aligned += 1
        elif base_score > aligned_score:
            winner = "base"
            wins_base += 1
        else:
            winner = "tie"
            ties += 1

        print(f"  Base score: {base_score:.1f} | Aligned score: {aligned_score:.1f} | Winner: {winner}")

        details.append({
            "prompt": prompt,
            "base_score": base_score,
            "aligned_score": aligned_score,
            "winner": winner,
            "base_response": base_response[:200],
            "aligned_response": aligned_response[:200],
        })

    # Summary
    total = len(EVAL_PROMPTS)
    print(f"\n{'=' * 60}")
    print("  RESULTS")
    print(f"{'=' * 60}")
    print(f"  Aligned wins:  {wins_aligned}/{total} ({wins_aligned/total*100:.0f}%)")
    print(f"  Base wins:     {wins_base}/{total} ({wins_base/total*100:.0f}%)")
    print(f"  Ties:          {ties}/{total} ({ties/total*100:.0f}%)")
    print(f"\n  Aligned model win rate: {wins_aligned / total * 100:.1f}%")

    if wins_aligned > wins_base:
        print("\n  DPO alignment improved response quality!")
    elif wins_aligned == wins_base:
        print("\n  Results are mixed — try collecting more preference data or adjusting beta.")
    else:
        print("\n  Base model still winning — the preference data may need more variety.")

    # Save detailed results
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    output_path = os.path.join(results_dir, "evaluation_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "summary": {
                "aligned_wins": wins_aligned,
                "base_wins": wins_base,
                "ties": ties,
                "win_rate": wins_aligned / total,
            },
            "details": details,
        }, f, indent=2)

    print(f"\n  Detailed results: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
