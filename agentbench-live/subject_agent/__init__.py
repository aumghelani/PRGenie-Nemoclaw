"""Subject Agent — the agent under benchmark.

Runs a 4-LLM-call research loop with 4-8 tool invocations per task.
This is the workload that gets profiled, optimized, and re-run.
"""
from .agent import SubjectAgent, run_task
from .telemetry import TelemetryCollector, Span

__all__ = ["SubjectAgent", "run_task", "TelemetryCollector", "Span"]
