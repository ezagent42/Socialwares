"""Socialware App backend — FastAPI entry point.

Minimal template. Users incrementally grow on this foundation (P1->P5).
Start: uvicorn src.app:app --port 8001
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="Socialware App",
    description="Web application for agent interaction visualization",
    version="0.1.0",
)


VIOLATIONS_DIR = Path(".runtime/data/evolve/violations")


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


@app.get("/violations")
async def list_violations() -> list[dict]:
    """List unresolved constraint violations."""
    violations = []
    VIOLATIONS_DIR.mkdir(parents=True, exist_ok=True)
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
    VIOLATIONS_DIR.mkdir(parents=True, exist_ok=True)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
