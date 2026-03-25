# P0 ZChat 互联 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable Agent-to-Agent communication across Socialware Apps via ZChat (Zenoh P2P). AgentForge can receive requests from other Apps (e.g. TaskArena requests a new role), and SOUL.md becomes discoverable for service advertisement.

**Architecture:** ZChat uses Zenoh pub/sub for P2P messaging between Socialware Apps. Each App exposes its scope/SOUL.md as a service descriptor. A `/zchat` endpoint receives inbound messages and routes them to the active Agent session. An outbound `/zchat/send` endpoint lets Agents send messages to other Apps. The Zenoh transport layer is abstracted so it can be swapped for HTTP in development.

**Tech Stack:** Python (FastAPI, pydantic), Zenoh Python SDK (zenoh-python), pytest

**Reference:** `docs/plans/2026-03-19-socialware-framework-design.md` (第七部分: Phase 0)

**Note:** This is the most experimental phase. Zenoh integration may be replaced with simpler HTTP-based inter-app communication initially.

---

### Task 1: Define ZChat message protocol

**Files:**
- Create: `src/zchat.py`
- Test: `tests/test_zchat.py`

**Step 1: Write the failing test**

Create `tests/test_zchat.py`:

```python
"""Tests for ZChat message protocol and routing."""
from __future__ import annotations

from src.zchat import ZChatMessage, ZChatRouter


class TestZChatMessage:
    def test_create_message(self):
        msg = ZChatMessage(
            from_app="agentforge.socialware.app",
            from_role="agentforge",
            to_app="taskarena.socialware.app",
            to_role="default",
            intent="create_role",
            payload={"name": "notifier", "description": "Notification agent"},
        )
        assert msg.from_app == "agentforge.socialware.app"
        assert msg.intent == "create_role"

    def test_message_to_dict(self):
        msg = ZChatMessage(
            from_app="a", from_role="r1",
            to_app="b", to_role="r2",
            intent="test", payload={},
        )
        d = msg.to_dict()
        assert d["from"] == "a/r1"
        assert d["to"] == "b/r2"
        assert d["intent"] == "test"


class TestZChatRouter:
    def test_router_registers_handler(self):
        router = ZChatRouter()
        router.register("create_role", lambda msg: {"status": "ok"})
        assert "create_role" in router.handlers

    def test_router_dispatches(self):
        router = ZChatRouter()
        result = []
        router.register("ping", lambda msg: result.append("pong"))
        msg = ZChatMessage(
            from_app="a", from_role="r1",
            to_app="b", to_role="r2",
            intent="ping", payload={},
        )
        router.dispatch(msg)
        assert result == ["pong"]
```

**Step 2: Run test to verify it fails**

**Step 3: Implement ZChat protocol**

Create `src/zchat.py`:

```python
"""ZChat — Agent-to-Agent communication protocol.

Defines message format and routing for inter-App communication.
Transport layer (Zenoh/HTTP) is pluggable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ZChatMessage:
    """A message between two Socialware App agents."""
    from_app: str
    from_role: str
    to_app: str
    to_role: str
    intent: str
    payload: dict[str, Any] = field(default_factory=dict)
    reply_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": f"{self.from_app}/{self.from_role}",
            "to": f"{self.to_app}/{self.to_role}",
            "intent": self.intent,
            "payload": self.payload,
            "reply_to": self.reply_to,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ZChatMessage:
        from_parts = d["from"].split("/", 1)
        to_parts = d["to"].split("/", 1)
        return cls(
            from_app=from_parts[0],
            from_role=from_parts[1] if len(from_parts) > 1 else "default",
            to_app=to_parts[0],
            to_role=to_parts[1] if len(to_parts) > 1 else "default",
            intent=d["intent"],
            payload=d.get("payload", {}),
            reply_to=d.get("reply_to"),
        )


class ZChatRouter:
    """Routes incoming ZChat messages to registered handlers."""

    def __init__(self):
        self.handlers: dict[str, Callable] = {}

    def register(self, intent: str, handler: Callable) -> None:
        self.handlers[intent] = handler

    def dispatch(self, message: ZChatMessage) -> Any:
        handler = self.handlers.get(message.intent)
        if handler:
            return handler(message)
        return {"error": f"No handler for intent: {message.intent}"}
```

**Step 4: Run test to verify it passes**

**Step 5: Commit**

```bash
git add src/zchat.py tests/test_zchat.py
git commit -m "feat(zchat): define ZChat message protocol and router for P0"
```

---

### Task 2: Backend — ZChat endpoints

**Files:**
- Modify: `src/app.py`
- Modify: `tests/test_zchat.py`

**Step 1: Write tests**

Add to `tests/test_zchat.py`:

```python
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


class TestZChatEndpoints:
    def test_zchat_receive(self):
        r = client.post("/zchat/receive", json={
            "from": "taskarena.app/default",
            "to": "agentforge.app/agentforge",
            "intent": "ping",
            "payload": {},
        })
        assert r.status_code == 200

    def test_zchat_discover(self):
        r = client.get("/zchat/discover")
        assert r.status_code == 200
        assert "soul" in r.json()
        assert "app" in r.json()
```

**Step 2: Implement endpoints**

Add to `src/app.py`:

```python
from src.zchat import ZChatMessage, ZChatRouter

_zchat_router = ZChatRouter()

@app.post("/zchat/receive")
async def zchat_receive(msg: dict):
    """Receive a ZChat message from another App."""
    zchat_msg = ZChatMessage.from_dict(msg)
    result = _zchat_router.dispatch(zchat_msg)
    return {"status": "received", "result": result}

@app.get("/zchat/discover")
async def zchat_discover():
    """Expose this App's SOUL.md for service discovery."""
    soul_path = AGENT_DIR / "scope" / "SOUL.md"
    soul = soul_path.read_text(encoding="utf-8") if soul_path.exists() else ""
    return {"app": "socialware", "soul": soul}

@app.post("/zchat/send")
async def zchat_send(msg: dict):
    """Send a ZChat message to another App (HTTP transport)."""
    target_url = msg.get("target_url", "")
    if not target_url:
        raise HTTPException(400, "target_url required")
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{target_url}/zchat/receive", json=msg)
        return {"status": "sent", "response": r.json()}
```

**Step 3: Run tests**

**Step 4: Commit**

```bash
git add src/app.py tests/test_zchat.py
git commit -m "feat(api): add ZChat receive/discover/send endpoints for P0"
```

---

### Task 3: Create zchat Skill for AgentForge

**Files:**
- Create: `.socialware/workspace/my-team/agentforge/agent/flow/zchat_connect/SKILL.md`
- Modify: `.socialware/workspace/my-team/agentforge/agent/flow/flow.yaml`

**Step 1: Create SKILL.md**

```markdown
---
name: zchat_connect
description: "Connect to another Socialware App via ZChat for inter-agent communication"
---

# ZChat Connect

## Trigger

User says "connect to", "zchat", "talk to another app", etc.

## Flow

1. Ask for the target App URL (e.g. https://taskarena.socialware.app)
2. Discover the target App: `GET {url}/zchat/discover`
3. Display the target's SOUL.md (what it can do)
4. Ask what intent to send
5. Send message: `POST /zchat/send` with target_url and intent
6. Display the response

## API

```bash
# Discover another app
curl https://taskarena.socialware.app/zchat/discover

# Send a message
curl -X POST http://localhost:8001/zchat/send \
  -H "Content-Type: application/json" \
  -d '{
    "from": "agentforge.app/agentforge",
    "to": "taskarena.app/default",
    "intent": "create_role",
    "payload": {"name": "notifier"},
    "target_url": "https://taskarena.socialware.app"
  }'
```
```

**Step 2: Update flow.yaml**

Add:
```yaml
  - action: zchat_connect
    role: [agentforge]
    description: "Connect to another Socialware App via ZChat"
```

**Step 3: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/flow/zchat_connect/
git add .socialware/workspace/my-team/agentforge/agent/flow/flow.yaml
git commit -m "feat(agentforge): add zchat_connect skill for P0 inter-agent communication"
```

---

### Task 4: Full verification

**Step 1:** Run all tests
**Step 2:** Test ZChat locally (two instances talking to each other)
**Step 3:** Final commit

---

## Summary

| Task | What | Key Files |
|------|------|-----------|
| 1 | ZChat message protocol | `src/zchat.py`, `tests/test_zchat.py` |
| 2 | ZChat API endpoints | `src/app.py` `/zchat/receive` + `/zchat/discover` + `/zchat/send` |
| 3 | zchat_connect Skill | AgentForge `flow/zchat_connect/SKILL.md` |
| 4 | Full verification | All tests pass, local inter-app test |

---

## Future: Zenoh Transport

The current implementation uses HTTP for inter-app communication. When Zenoh is integrated:

1. Replace `/zchat/send` HTTP call with Zenoh pub/sub
2. Replace `/zchat/receive` HTTP endpoint with Zenoh subscriber
3. Keep `/zchat/discover` as HTTP (service discovery remains HTTP-based)
4. ZChatMessage format stays the same — only transport changes
