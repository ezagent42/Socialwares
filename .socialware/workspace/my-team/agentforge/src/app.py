"""Socialware App backend — FastAPI entry point.

Minimal template. Users incrementally grow on this foundation (P1->P5).
Start: uv run uvicorn src.app:app --port $APP_PORT
"""
from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()  # must be before other imports that read env vars

import json
import os
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

# App config — agent reads these to know where the API is
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8001"))

app = FastAPI(
    title="Socialware App",
    description="Web application for agent interaction visualization",
    version="0.1.0",
)


from src.db import Database
from src.auth import github_login, github_callback, get_current_user, logout
from src.session import SessionManager

# Database instance
_db: Database | None = None

async def get_db() -> Database:
    global _db
    if _db is None:
        db_path = Path(".runtime/data/Sqlite/agentforge.db")
        _db = Database(db_path)
        await _db.init()
        # Seed example agent on first init
        from src.seed import seed_example_agent
        await seed_example_agent(_db)
    return _db

VIOLATIONS_DIR = Path(".runtime/data/evolve/violations")


@app.get("/api/auth/login")
async def auth_login(request: Request):
    return await github_login(request)

@app.get("/api/auth/callback")
async def auth_callback(request: Request, code: str):
    db = await get_db()
    return await github_callback(code, db)

@app.get("/api/auth/me")
async def auth_me(request: Request):
    db = await get_db()
    return await get_current_user(request, db)

@app.post("/api/auth/logout")
async def auth_logout(request: Request):
    db = await get_db()
    return await logout(request, db)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


@app.get("/violations")
async def list_violations() -> list[dict]:
    """List unresolved constraint violations."""
    violations = []
    if not VIOLATIONS_DIR.exists():
        return violations
    for f in VIOLATIONS_DIR.glob("*.jsonl"):
        for line in f.read_text().splitlines():
            if line.strip():
                v = json.loads(line)
                if not v.get("resolved", False):
                    violations.append(v)
    return violations


@app.post("/violations/{violation_id}/resolve")
async def resolve_violation(violation_id: str) -> dict:
    """Mark a violation as resolved."""
    if not VIOLATIONS_DIR.exists():
        raise HTTPException(404, f"Violation {violation_id} not found")
    for f in VIOLATIONS_DIR.glob("*.jsonl"):
        lines = f.read_text().splitlines()
        updated = []
        found = False
        for line in lines:
            if line.strip():
                v = json.loads(line)
                if v.get("id") == violation_id:
                    v["resolved"] = True
                    v["resolved_at"] = datetime.now(timezone.utc).isoformat()
                    found = True
                updated.append(json.dumps(v, ensure_ascii=False))
        if found:
            f.write_text("\n".join(updated) + "\n")
            return {"status": "resolved", "id": violation_id}
    raise HTTPException(404, f"Violation {violation_id} not found")


# Session manager (singleton)
_session_manager = SessionManager()

@app.post("/api/chat/send")
async def chat_send(request: Request):
    """Receive user message. Must be authenticated."""
    db = await get_db()
    user = await get_current_user(request, db)
    body = await request.json()
    message = body.get("message", "")
    if not message:
        raise HTTPException(400, "Message is required")

    # Stream response via SSE
    async def event_generator():
        async for event in _session_manager.send(user["id"], message, db):
            yield event

    return EventSourceResponse(event_generator())


@app.get("/api/export/{agent_id}")
async def export_download(agent_id: str, request: Request):
    """Download agent config as zip file."""
    from fastapi.responses import FileResponse
    from src.crud.export import export_agent_zip

    db = await get_db()
    user = await get_current_user(request, db)

    # Verify agent belongs to user
    from src.crud.agent_crud import get_agent
    await get_agent(db, user["id"], agent_id)

    zip_path, agent_name = await export_agent_zip(db, agent_id)
    return FileResponse(
        path=str(zip_path),
        filename=f"{agent_name}.zip",
        media_type="application/zip",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
