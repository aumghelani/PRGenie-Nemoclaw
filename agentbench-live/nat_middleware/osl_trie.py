"""Output Sequence Length (OSL) predictor — trie over recent agent trajectories.

Battle plan §1: NAT profiles 20% of the agent's tool-calling trajectories,
builds a trie model, and predicts future OSL with ~90% accuracy. We ship
a small CPU-side trie keyed on the (system_prompt_hash, request_class,
last_tool_name) tuple → median observed output_tokens.
"""
from __future__ import annotations

import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


class OSLTriePredictor:
    def __init__(self, store_path: str | None = None) -> None:
        self.store_path = Path(store_path) if store_path else None
        self._counts: dict[tuple, list[int]] = defaultdict(list)
        if self.store_path and self.store_path.exists():
            self._load()

    @staticmethod
    def _key(system_prompt: str, request_class: str, last_tool: str | None) -> tuple:
        h = hashlib.md5(system_prompt.encode()).hexdigest()[:12]
        return (h, request_class, last_tool or "")

    def observe(
        self,
        system_prompt: str,
        request_class: str,
        last_tool: str | None,
        output_tokens: int,
    ) -> None:
        self._counts[self._key(system_prompt, request_class, last_tool)].append(output_tokens)

    def predict(
        self,
        system_prompt: str,
        request_class: str,
        last_tool: str | None,
        default: int = 256,
    ) -> int:
        observations = self._counts.get(self._key(system_prompt, request_class, last_tool), [])
        if len(observations) < 3:
            return default
        return int(statistics.median(observations))

    def confidence(
        self,
        system_prompt: str,
        request_class: str,
        last_tool: str | None,
    ) -> float:
        observations = self._counts.get(self._key(system_prompt, request_class, last_tool), [])
        if len(observations) < 5:
            return 0.0
        # Coefficient of variation, inverted — tight distribution = high confidence.
        mean = statistics.mean(observations)
        if mean == 0:
            return 0.0
        cv = statistics.pstdev(observations) / mean
        return max(0.0, min(1.0, 1.0 - cv))

    def save(self) -> None:
        if not self.store_path:
            return
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        # Tuple keys aren't JSON-serializable — convert to "|"-joined string.
        serial = {"|".join(map(str, k)): v for k, v in self._counts.items()}
        self.store_path.write_text(json.dumps(serial))

    def _load(self) -> None:
        assert self.store_path is not None
        raw = json.loads(self.store_path.read_text())
        for k_str, v in raw.items():
            parts = k_str.split("|")
            self._counts[tuple(parts)] = list(v)

    def stats(self) -> dict[str, Any]:
        total = sum(len(v) for v in self._counts.values())
        return {"unique_keys": len(self._counts), "total_observations": total}
