"""Optimizer Agent — meta-agent that analyzes a benchmark trace and
recommends vLLM configuration changes.

Inputs:  a TelemetryCollector trace (or BenchmarkResult)
Outputs: a list of human-readable recommendations + a vLLM CLI flag diff
"""
from .analyzer import TraceAnalyzer, CriticalPath, ParallelismOpportunity
from .recommender import Recommender, Recommendation

__all__ = [
    "TraceAnalyzer",
    "CriticalPath",
    "ParallelismOpportunity",
    "Recommender",
    "Recommendation",
]
