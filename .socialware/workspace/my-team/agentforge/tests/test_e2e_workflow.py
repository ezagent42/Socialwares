"""E2E: Full workflow — Create → List → View → Add Skill → Export → Delete."""
import pytest
import asyncio
import json

from src.db import Database
from src.session import SessionManager


@pytest.fixture(autouse=True)
def _disable_sdk(monkeypatch):
    """Force fallback path for E2E tests."""
    import src.claude_adapter
    monkeypatch.setattr(src.claude_adapter, "is_sdk_available", lambda: False)


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    asyncio.run(database.init())
    return database


@pytest.fixture
def user_id(db):
    async def _setup():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('u1', 1, 'test')")
        await conn.commit()
        await conn.close()
        return "u1"
    return asyncio.run(_setup())


def test_full_workflow(db, user_id):
    sm = SessionManager()

    # Create
    asyncio.run(_collect(sm, user_id, "/create-agent", db))
    asyncio.run(_collect(sm, user_id, "workflow-test", db))
    asyncio.run(_collect(sm, user_id, "# Workflow\nTest agent.", db))
    asyncio.run(_collect(sm, user_id, "done", db))
    events = asyncio.run(_collect(sm, user_id, "create", db))
    s = _structured(events)
    assert s is not None
    assert s["action"] == "created"
    agent = s["data"]

    # List
    events = asyncio.run(_collect(sm, user_id, "/list-agents", db))
    listed = _structured(events)["data"]["agents"]
    assert any(a["name"] == "workflow-test" for a in listed)

    # View
    view_msg = f'```ui_action\n{{"entity":"agent","action":"detail","targets":[{{"id":"{agent["id"]}","name":"workflow-test"}}]}}\n```'
    events = asyncio.run(_collect(sm, user_id, view_msg, db))
    detail = _structured(events)
    assert detail["action"] == "detailed"
    assert detail["data"]["role_md"] == "# Workflow\nTest agent."

    # Export (select format)
    events = asyncio.run(_collect(sm, user_id, "/export-agent", db))
    events = asyncio.run(_collect(sm, user_id, "workflow-test", db))
    assert "format" in _text(events).lower()
    events = asyncio.run(_collect(sm, user_id, "gitagent", db))
    s = _structured(events)
    assert s["action"] == "exported"
    assert "download_url" in s["data"]

    # Delete
    del_msg = f'```ui_action\n{{"entity":"agent","action":"delete","targets":[{{"id":"{agent["id"]}","name":"workflow-test"}}]}}\n```'
    events = asyncio.run(_collect(sm, user_id, del_msg, db))
    assert _structured(events)["action"] == "confirm_required"
    events = asyncio.run(_collect(sm, user_id, "confirm", db))
    assert "deleted" in _text(events).lower()


async def _collect(sm, uid, msg, db):
    events = []
    async for e in sm.send(uid, msg, db):
        events.append(e)
    return events


def _text(events):
    for e in events:
        if e["event"] == "text":
            return json.loads(e["data"]).get("content", "")
    return ""


def _structured(events):
    for e in events:
        if e["event"] == "structured":
            return json.loads(e["data"])
    return None
