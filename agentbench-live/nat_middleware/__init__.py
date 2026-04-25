"""NeMo Agent Toolkit middleware — header injection + OSL trie predictor.

Sits between the agent client and vLLM. In production this would hook
into NAT proper; for the hackathon we ship a thin compatible layer.
"""
from .headers import NvExtHeaders, build_headers
from .osl_trie import OSLTriePredictor

__all__ = ["NvExtHeaders", "build_headers", "OSLTriePredictor"]
