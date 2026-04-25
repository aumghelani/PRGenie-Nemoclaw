"""
Reward Ranker — Score responses with the trained reward model.

Generates multiple responses to test prompts and uses the reward model
to score them, demonstrating that the model learned human preferences.

Prerequisites:
    - Trained reward model via train_reward_model.py
    - vLLM server running

Usage:
    python3 score_responses.py
"""

import json
import os

import httpx
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REWARD_MODEL_DIR = os.path.join(SCRIPT_DIR, "reward-model")
VLLM_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
MODEL = "/models/llama-3.1-8b-instruct"

TEST_PROMPTS = [
    "Explain what version control is and why developers use it.",
    "Write a Python function that calculates the factorial of a number.",
    "What advice would you give to someone starting their first software engineering job?",
]


def load_reward_model():
    """Load the trained reward model."""
    if not os.path.exists(REWARD_MODEL_DIR):
        print(f"ERROR: Reward model not found at {REWARD_MODEL_DIR}")
        print("Run 'python3 train_reward_model.py' first.")
        raise SystemExit(1)

    tokenizer = AutoTokenizer.from_pretrained(REWARD_MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(REWARD_MODEL_DIR)
    model.eval()
    return tokenizer, model


def generate_response(prompt: str, temperature: float) -> str:
    """Generate a response from vLLM."""
    r = httpx.post(
        f"{VLLM_URL}/chat/completions",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 256,
            "temperature": temperature,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def score_response(prompt: str, response: str, tokenizer, model) -> float:
    """Score a (prompt, response) pair with the reward model."""
    text = f"Prompt: {prompt}\n\nResponse: {response}"
    inputs = tokenizer(text, truncation=True, max_length=512, return_tensors="pt")
    with torch.no_grad():
        output = model(**inputs)
    return output.logits.item()


def main():
    print("=" * 55)
    print("  Reward Ranker — Scoring Responses")
    print("=" * 55)

    tokenizer, reward_model = load_reward_model()

    for prompt in TEST_PROMPTS:
        print(f"\nPrompt: {prompt}")
        print("-" * 55)

        # Generate responses at different temperatures
        temps = [0.2, 0.7, 1.2]
        scored = []

        for temp in temps:
            response = generate_response(prompt, temp)
            score = score_response(prompt, response, tokenizer, reward_model)
            scored.append((temp, score, response))

        # Sort by reward score (highest = best)
        scored.sort(key=lambda x: x[1], reverse=True)

        for rank, (temp, score, response) in enumerate(scored, 1):
            preview = response[:120].replace("\n", " ") + "..."
            print(f"  #{rank} [score={score:.3f}, temp={temp}] {preview}")

    print(f"\n{'=' * 55}")
    print("  The reward model ranks responses based on your preferences!")
    print("  Higher score = more aligned with what you rated as 'better'.")
    print("=" * 55)


if __name__ == "__main__":
    main()
