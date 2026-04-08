# TDD Guide for Socialware Apps

## Mapping: Action → API → Test

TDD development in Socialware follows a three-layer mapping:

```
socialware.py                 src/api.py                  tests/test_api.py
─────────────                 ──────────                  ─────────────────
app.action("check_health")  → @app.get("/health")       → test_health()
app.action("create_task")   → @app.post("/tasks")       → test_create_task()
app.action("list_tasks")    → @app.get("/tasks")        → test_list_tasks()
app.action("resolve_task")  → @app.post("/tasks/{id}")  → test_resolve_task()
```

Each business operation registered via `app.action(...)` should have a corresponding API endpoint and test case.

## Example Test Structure

```python
"""tests/test_api.py — Socialware App API tests."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import app


@pytest.fixture
async def client():
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Health ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    """GET /health should return status ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── Business operation example: create_task ──────────

@pytest.mark.asyncio
async def test_create_task(client):
    """POST /tasks should create a task and return an id."""
    payload = {"title": "Write unit tests", "assignee": "default"}
    resp = await client.post("/tasks", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Write unit tests"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_task_missing_title(client):
    """POST /tasks should return 422 when title is missing."""
    resp = await client.post("/tasks", json={"assignee": "default"})
    assert resp.status_code == 422


# ── Business operation example: list_tasks ───────────

@pytest.mark.asyncio
async def test_list_tasks(client):
    """GET /tasks should return a list of tasks."""
    resp = await client.get("/tasks")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

## Example API Endpoint Implementation

```python
"""src/api.py — Pattern for adding business endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ── Request / Response Models ─────────────────────────

class TaskCreate(BaseModel):
    title: str
    assignee: str = "default"


class TaskResponse(BaseModel):
    id: str
    title: str
    assignee: str
    created_at: str


# ── In-memory store (replace with persistent storage) ─

_tasks: dict[str, dict] = {}


# ── Endpoints ─────────────────────────────────────────

@app.post("/tasks", response_model=TaskResponse)
async def create_task(payload: TaskCreate) -> dict:
    """Create a new task."""
    task_id = uuid.uuid4().hex[:8]
    task = {
        "id": task_id,
        "title": payload.title,
        "assignee": payload.assignee,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _tasks[task_id] = task
    return task


@app.get("/tasks")
async def list_tasks() -> list[dict]:
    """List all tasks."""
    return list(_tasks.values())


@app.post("/tasks/{task_id}/resolve")
async def resolve_task(task_id: str) -> dict:
    """Mark a task as resolved."""
    if task_id not in _tasks:
        raise HTTPException(404, f"Task {task_id} not found")
    _tasks[task_id]["resolved"] = True
    _tasks[task_id]["resolved_at"] = datetime.now(timezone.utc).isoformat()
    return _tasks[task_id]
```

## How to Run Tests

```bash
# Run all tests (verbose output)
uv run pytest tests/ -v

# Run a specific test
uv run pytest tests/test_api.py -v -k test_create_task

# Run with coverage report
uv run pytest tests/ -v --cov=src --cov-report=term-missing
```

## TDD Cycle Checklist

1. **Red**: Write the test first, run it and confirm it fails
2. **Green**: Write the minimum code to make the test pass
3. **Refactor**: Refactor the code (add types, models, error handling), ensure tests still pass
4. **Repeat**: Repeat the above steps for the next action

## Tips

- Implement only one action's API endpoint at a time
- Test cases should cover both happy paths and error paths (e.g., missing fields, resource not found)
- Use Pydantic `BaseModel` for request validation — FastAPI will automatically return 422
- Keep endpoint functions concise; extract complex logic into a service layer
- SKILL.md also needs "testing" — check that trigger, flow, and error handling are complete
