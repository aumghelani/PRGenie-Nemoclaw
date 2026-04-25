from contextlib import asynccontextmanager
from fastapi import FastAPI

from backend.config import settings
from backend.db.session import init_engine
from backend.routers import dashboard, health, webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()  # creates tables if missing
    yield


app = FastAPI(
    title="PRGenie",
    description="GitHub-native AI agent for PR triage, trust scoring, and issue demand.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(webhook.router)
app.include_router(dashboard.router)


@app.get("/api/info")
async def info() -> dict:
    return {
        "service": "prclaw",
        "mock_mode": settings.MOCK_MODE,
        "model": settings.VLLM_MODEL,
    }
