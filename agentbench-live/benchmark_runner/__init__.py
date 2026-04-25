"""Benchmark Runner — runs the Subject Agent in baseline vs optimized modes.

Produces a JSON file per run + an aggregated comparison report.
"""
from .runner import BenchmarkRunner, BenchmarkConfig, BenchmarkResult
from .tasks import BENCHMARK_TASKS

__all__ = ["BenchmarkRunner", "BenchmarkConfig", "BenchmarkResult", "BENCHMARK_TASKS"]
