"""AgentBench Live API server.

Endpoints:
    GET  /health
    GET  /tasks                       — list benchmark tasks
    POST /benchmark/run               — start a benchmark run, returns run_id
    GET  /benchmark/{run_id}          — fetch result
    WS   /ws/{run_id}                 — stream span events as the agent runs
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from benchmark_runner import BENCHMARK_TASKS
from benchmark_runner.tasks import get_task
from optimizer_agent import Recommender, TraceAnalyzer
from subject_agent.agent import AgentConfig, SubjectAgent
from subject_agent.telemetry import TelemetryCollector

app = FastAPI(title="AgentBench Live", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon — tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory run registry. (Hackathon — fine. For prod, swap to Redis.)
_RUNS: dict[str, dict[str, Any]] = {}
_QUEUES: dict[str, asyncio.Queue] = {}


VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:5000/v1")
VLLM_MODEL = os.getenv("VLLM_MODEL", "nemotron")


class RunRequest(BaseModel):
    task_id: str
    mode: str  # "baseline" | "optimized"
    repeats: int = 1


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "vllm_base_url": VLLM_BASE_URL, "vllm_model": VLLM_MODEL}


@app.get("/tasks")
async def list_tasks() -> list[dict[str, Any]]:
    return [
        {
            "id": t.id,
            "title": t.title,
            "query": t.query,
            "expected_tool_calls": t.expected_tool_calls,
            "notes": t.notes,
        }
        for t in BENCHMARK_TASKS
    ]


@app.post("/benchmark/run")
async def start_run(req: RunRequest) -> dict[str, Any]:
    try:
        task = get_task(req.task_id)
    except KeyError:
        raise HTTPException(404, f"unknown task {req.task_id}")
    if req.mode not in ("baseline", "optimized"):
        raise HTTPException(400, "mode must be baseline|optimized")

    run_id = uuid.uuid4().hex[:12]
    queue: asyncio.Queue = asyncio.Queue()
    _QUEUES[run_id] = queue
    _RUNS[run_id] = {"status": "running", "task_id": req.task_id, "mode": req.mode}

    asyncio.create_task(_execute(run_id, task.query, req.mode, queue))
    return {"run_id": run_id}


@app.get("/benchmark/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    if run_id not in _RUNS:
        raise HTTPException(404, "unknown run_id")
    return _RUNS[run_id]


@app.websocket("/ws/{run_id}")
async def stream(ws: WebSocket, run_id: str) -> None:
    await ws.accept()
    queue = _QUEUES.get(run_id)
    if queue is None:
        await ws.send_json({"event": "error", "message": "unknown run_id"})
        await ws.close()
        return

    try:
        while True:
            event = await queue.get()
            await ws.send_json(event)
            if event.get("event") == "done":
                break
    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------- runner core


class _StreamingCollector(TelemetryCollector):
    """TelemetryCollector that emits span-open / span-close events to a queue."""

    def __init__(self, run_id: str, mode: str, queue: asyncio.Queue) -> None:
        super().__init__(run_id=run_id, mode=mode)
        self._queue = queue

    def _emit(self, event_type: str, span) -> None:
        self._queue.put_nowait(
            {"event": event_type, "run_id": self.run_id, "span": span.to_dict()}
        )

    # Override span() to emit events.
    def span(self, name, kind, **attrs):
        cm = super().span(name, kind, **attrs)

        # Wrap the context manager so we can emit on enter/exit.
        outer = self

        class _Wrapped:
            def __enter__(self_inner):
                span = cm.__enter__()
                outer._emit("span.start", span)
                self_inner._span = span
                return span

            def __exit__(self_inner, *exc):
                cm.__exit__(*exc)
                outer._emit("span.end", self_inner._span)
                return False

        return _Wrapped()


async def _execute(run_id: str, query: str, mode: str, queue: asyncio.Queue) -> None:
    config = AgentConfig(
        base_url=VLLM_BASE_URL,
        model=VLLM_MODEL,
        nvext_priority="high" if mode == "optimized" else None,
        nvext_latency_sensitive=True if mode == "optimized" else None,
    )
    collector = _StreamingCollector(run_id=run_id, mode=mode, queue=queue)
    agent = SubjectAgent(config, collector)

    try:
        result = await agent.run(query)
        trace = result["trace"]

        # Run the optimizer agent on the trace right away.
        analyzer = TraceAnalyzer(trace)
        recs = Recommender(analyzer).recommend()

        _RUNS[run_id] = {
            "status": "completed",
            "task_id": _RUNS[run_id]["task_id"],
            "mode": mode,
            "trace": trace,
            "recommendations": [r.to_dict() for r in recs],
            "answer": result["answer"],
        }
        await queue.put(
            {
                "event": "done",
                "run_id": run_id,
                "summary": trace.get("summary"),
                "recommendations": [r.to_dict() for r in recs],
            }
        )
    except Exception as e:
        _RUNS[run_id] = {**_RUNS[run_id], "status": "error", "error": str(e)}
        await queue.put({"event": "error", "run_id": run_id, "message": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
