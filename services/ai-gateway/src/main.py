"""
Entry point for the Zero Trust AI Gateway service.
Runs a FastAPI server that sits between AI agents and their tools.
Every agent action passes through 5 middleware stages before approval.

How to run: uvicorn src.main:app --host 0.0.0.0 --port 8000
"""
import logging
from fastapi import FastAPI
from src.config import settings
from src.routers import agents, admin

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Zero Trust AI Gateway",
    description="Zero Trust enforcement layer for agentic AI systems",
    version="1.0.0",
)

app.include_router(agents.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ai-gateway"}


@app.get("/")
async def root():
    return {
        "service": "Zero Trust AI Gateway",
        "version": "1.0.0",
        "status": "running",
        "pipeline": ["auth", "policy", "rate_limit", "prompt_inspection", "audit"],
    }
