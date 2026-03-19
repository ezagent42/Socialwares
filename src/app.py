"""Socialware App backend — FastAPI entry point.

Minimal template. Users incrementally grow on this foundation (P1->P5).
Start: uvicorn src.app:app --port 8001
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="Socialware App",
    description="Web application for agent interaction visualization",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
