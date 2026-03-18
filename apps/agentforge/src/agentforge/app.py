"""AgentForge FastAPI application.

Mock implementation — agent lifecycle management.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Header

app = FastAPI(title="AgentForge", version="0.1.0")

_agents: dict[str, dict[str, Any]] = {}

VALID_TRANSITIONS = {
    ("created", "spawn"): "active",
    ("active", "sleep"): "sleeping",
    ("sleeping", "wake"): "active",
    ("active", "destroy"): "destroyed",
    ("sleeping", "destroy"): "destroyed",
}


@app.post("/agents/spawn")
def spawn_agent(
    data: dict[str, Any],
    x_identity: str = Header(default="anonymous"),
) -> dict[str, Any]:
    name = data.get("name", f"agent-{len(_agents)+1}")
    agent = {
        "name": name,
        "template": data.get("template", "default"),
        "status": "created",
        "adapter": data.get("adapter", "claude"),
        "owner": x_identity,
        "parent": data.get("parent"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _agents[name] = agent
    # Auto-transition to active
    agent["status"] = "active"
    return agent


@app.get("/agents")
def list_agents(status: str | None = None) -> list[dict[str, Any]]:
    agents = list(_agents.values())
    if status:
        agents = [a for a in agents if a["status"] == status]
    return agents


@app.get("/agents/{name}")
def get_agent(name: str) -> dict[str, Any]:
    if name not in _agents:
        raise HTTPException(404, f"Agent {name} not found")
    return _agents[name]


@app.post("/agents/{name}/wake")
def wake_agent(name: str) -> dict[str, Any]:
    if name not in _agents:
        raise HTTPException(404, f"Agent {name} not found")
    agent = _agents[name]
    key = (agent["status"], "wake")
    if key not in VALID_TRANSITIONS:
        raise HTTPException(409, f"Cannot wake agent in status {agent['status']}")
    agent["status"] = VALID_TRANSITIONS[key]
    return agent


@app.post("/agents/{name}/sleep")
def sleep_agent(name: str) -> dict[str, Any]:
    if name not in _agents:
        raise HTTPException(404, f"Agent {name} not found")
    agent = _agents[name]
    key = (agent["status"], "sleep")
    if key not in VALID_TRANSITIONS:
        raise HTTPException(409, f"Cannot sleep agent in status {agent['status']}")
    agent["status"] = VALID_TRANSITIONS[key]
    return agent


@app.post("/agents/{name}/destroy")
def destroy_agent(name: str) -> dict[str, Any]:
    if name not in _agents:
        raise HTTPException(404, f"Agent {name} not found")
    agent = _agents[name]
    key = (agent["status"], "destroy")
    if key not in VALID_TRANSITIONS:
        raise HTTPException(409, f"Cannot destroy agent in status {agent['status']}")
    agent["status"] = VALID_TRANSITIONS[key]
    return agent


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
