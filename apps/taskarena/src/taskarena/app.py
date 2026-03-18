"""TaskArena FastAPI application.

Mock implementation — returns stub data for all endpoints.
Four primitives (Role/Flow/Commitment/Arena) are defined in config
and enforced by pre_send middleware.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Header

app = FastAPI(title="TaskArena", version="0.1.0")

# In-memory mock store
_tasks: dict[str, dict[str, Any]] = {}
_counter = 0

# Flow state machine
VALID_TRANSITIONS = {
    ("draft", "propose"): "submitted",
    ("submitted", "review"): "under_review",
    ("under_review", "approve"): "approved",
    ("under_review", "reject"): "rejected",
    ("rejected", "resubmit"): "submitted",
    ("approved", "close"): "closed",
}


@app.post("/tasks")
def create_task(
    data: dict[str, Any],
    x_identity: str = Header(default="anonymous"),
) -> dict[str, Any]:
    global _counter
    _counter += 1
    task_id = f"task-{_counter:03d}"
    task = {
        "id": task_id,
        "title": data.get("title", "Untitled"),
        "description": data.get("description", ""),
        "budget": data.get("budget"),
        "status": "draft",
        "created_by": x_identity,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _tasks[task_id] = task
    return task


@app.get("/tasks")
def list_tasks(status: str | None = None) -> list[dict[str, Any]]:
    tasks = list(_tasks.values())
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, Any]:
    if task_id not in _tasks:
        raise HTTPException(404, f"Task {task_id} not found")
    return _tasks[task_id]


@app.put("/tasks/{task_id}")
def update_task(task_id: str, data: dict[str, Any]) -> dict[str, Any]:
    if task_id not in _tasks:
        raise HTTPException(404, f"Task {task_id} not found")
    _tasks[task_id].update(data)
    return _tasks[task_id]


@app.post("/tasks/{task_id}/review")
def review_task(
    task_id: str,
    data: dict[str, Any],
    x_identity: str = Header(default="anonymous"),
) -> dict[str, Any]:
    if task_id not in _tasks:
        raise HTTPException(404, f"Task {task_id} not found")

    task = _tasks[task_id]
    decision = data.get("decision")

    if decision == "approve":
        action = "approve"
    elif decision == "reject":
        action = "reject"
    else:
        raise HTTPException(400, f"Invalid decision: {decision}")

    key = (task["status"], action)
    if key not in VALID_TRANSITIONS:
        raise HTTPException(
            409,
            f"Cannot {action} task in status {task['status']}",
        )

    task["status"] = VALID_TRANSITIONS[key]
    task["review"] = {
        "decision": decision,
        "reason": data.get("reason", ""),
        "reviewer": x_identity,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    return task


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
