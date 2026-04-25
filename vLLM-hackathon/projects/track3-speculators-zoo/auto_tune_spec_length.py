"""
Adaptive speculation length — Deep Tech lane.

Observes acceptance rate per request, adjusts --num-speculative-tokens
for the next request toward the value that maximizes tokens-accepted-per-step.

Since vLLM doesn't (at time of writing) support runtime k changes via API,
this script instead drives multiple vLLM replicas on different ports, each
with a fixed k, and routes each request to the replica with the best
recent performance for the current workload pattern.

Think of it as a lightweight bandit over k ∈ {2, 3, 5, 7}.
"""

import argparse
import collections
import json
import random
import time
from typing import Dict, List

import httpx


# Replicas pre-started on these ports, each with a different k.
# Start them yourself with serve_configs/eagle.sh edited for each port/k,
# or adapt to call a supervisor script.
REPLICAS: Dict[int, str] = {
    2: "http://localhost:8002/v1",
    3: "http://localhost:8003/v1",
    5: "http://localhost:8005/v1",
    7: "http://localhost:8007/v1",
}

MODEL = "/models/llama-3.1-70b-instruct"

# Workload: rotates through different prompt shapes so adaptation can show value.
WORKLOAD = (
    ["short: explain in one word: " + w for w in "cat dog sun moon".split()] * 10 +
    ["medium: summarize in a paragraph: lorem ipsum dolor sit amet " * 3] * 10 +
    ["long: write a detailed essay on: the history of computation"] * 10
)


def pull_accept_rate(endpoint: str) -> float:
    try:
        text = httpx.get(endpoint.replace("/v1", "") + "/metrics", timeout=3).text
        accepted = next((float(l.split()[-1]) for l in text.splitlines()
                         if l.startswith("vllm:spec_decode_num_accepted_tokens")), 0.0)
        drafted = next((float(l.split()[-1]) for l in text.splitlines()
                        if l.startswith("vllm:spec_decode_num_draft_tokens")), 1.0)
        return accepted / max(drafted, 1.0)
    except httpx.HTTPError:
        return 0.0


def request(endpoint: str, prompt: str) -> float:
    """Returns tokens/sec for this single request."""
    t0 = time.time()
    r = httpx.post(
        f"{endpoint}/chat/completions",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 256,
            "temperature": 0.0,
        },
        timeout=180,
    )
    elapsed = time.time() - t0
    r.raise_for_status()
    toks = r.json()["usage"]["completion_tokens"]
    return toks / max(elapsed, 0.01)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epsilon", type=float, default=0.15,
                        help="Exploration rate for epsilon-greedy")
    args = parser.parse_args()

    # Moving average of throughput per k
    perf: Dict[int, collections.deque] = {k: collections.deque(maxlen=10) for k in REPLICAS}

    # Prime each with one measurement so we have something to compare
    for k, ep in REPLICAS.items():
        perf[k].append(request(ep, "warmup"))

    chosen_history: List[int] = []
    for i, prompt in enumerate(WORKLOAD):
        # Epsilon-greedy choice
        if random.random() < args.epsilon:
            k_choice = random.choice(list(REPLICAS))
        else:
            k_choice = max(perf, key=lambda k: sum(perf[k]) / len(perf[k]))

        tps = request(REPLICAS[k_choice], prompt)
        perf[k_choice].append(tps)
        chosen_history.append(k_choice)

        if (i + 1) % 10 == 0:
            avg = {k: round(sum(v)/len(v), 1) for k, v in perf.items()}
            most_recent = collections.Counter(chosen_history[-10:]).most_common()
            print(f"  step {i+1}: avg tok/s by k = {avg}  recently chose: {most_recent}")

    print(f"\nFinal k-preferences over {len(WORKLOAD)} requests:")
    print(f"  {dict(collections.Counter(chosen_history))}")


if __name__ == "__main__":
    main()
