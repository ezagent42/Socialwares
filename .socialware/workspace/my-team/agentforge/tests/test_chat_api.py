import pytest
import asyncio
import json


@pytest.fixture
def db(tmp_path):
    from src.db import Database
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


def test_send_text(db, user_id):
    from src.session import SessionManager
    sm = SessionManager()
    events = asyncio.run(_collect(sm, user_id, "hello", db))
    assert any(e["event"] == "text" for e in events)
    assert any(e["event"] == "done" for e in events)


def test_create_wizard_3_steps(db, user_id):
    from src.session import SessionManager
    sm = SessionManager()
    events = asyncio.run(_collect(sm, user_id, "/create-agent", db))
    assert "Step 1" in _text(events)
    events = asyncio.run(_collect(sm, user_id, "test-app", db))
    assert "Step 2" in _text(events)
    events = asyncio.run(_collect(sm, user_id, "# Test\nYou test.", db))
    assert "Step 3" in _text(events)
    events = asyncio.run(_collect(sm, user_id, "done", db))
    assert "Confirm" in _text(events) or "confirm" in _text(events).lower()
    events = asyncio.run(_collect(sm, user_id, "create", db))
    s = _structured(events)
    assert s is not None
    assert s["type"] == "agent"
    assert s["action"] == "created"
    assert s["data"]["name"] == "test-app"


def test_create_with_skill(db, user_id):
    from src.session import SessionManager
    sm = SessionManager()
    asyncio.run(_collect(sm, user_id, "/create-agent", db))
    asyncio.run(_collect(sm, user_id, "my-agent", db))
    asyncio.run(_collect(sm, user_id, "# My Agent", db))
    asyncio.run(_collect(sm, user_id, "ping", db))
    asyncio.run(_collect(sm, user_id, "Pings server", db))
    asyncio.run(_collect(sm, user_id, "done", db))
    events = asyncio.run(_collect(sm, user_id, "create", db))
    s = _structured(events)
    assert s is not None
    assert len(s["data"]["skills"]) == 1


def test_create_cancel(db, user_id):
    from src.session import SessionManager
    sm = SessionManager()
    asyncio.run(_collect(sm, user_id, "/create-agent", db))
    events = asyncio.run(_collect(sm, user_id, "cancel", db))
    assert "cancelled" in _text(events).lower()


def test_list_after_create(db, user_id):
    from src.session import SessionManager
    sm = SessionManager()
    asyncio.run(_collect(sm, user_id, "/create-agent", db))
    asyncio.run(_collect(sm, user_id, "list-test", db))
    asyncio.run(_collect(sm, user_id, "skip", db))
    asyncio.run(_collect(sm, user_id, "done", db))
    asyncio.run(_collect(sm, user_id, "create", db))
    events = asyncio.run(_collect(sm, user_id, "/list-agents", db))
    s = _structured(events)
    assert s is not None
    assert s["action"] == "listed"
    assert len(s["data"]["agents"]) >= 1


def test_ui_action_delete(db, user_id):
    from src.session import SessionManager
    sm = SessionManager()
    msg = '```ui_action\n{"entity": "agent", "action": "delete", "targets": [{"id": "a1", "name": "test"}]}\n```'
    events = asyncio.run(_collect(sm, user_id, msg, db))
    s = _structured(events)
    assert s is not None
    assert s["action"] == "confirm_required"


def test_chat_history_saved(db, user_id):
    from src.session import SessionManager
    sm = SessionManager()
    asyncio.run(_collect(sm, user_id, "hello", db))
    async def _check():
        conn = await db.connect()
        cursor = await conn.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ?", (user_id,))
        count = (await cursor.fetchone())[0]
        await conn.close()
        return count
    assert asyncio.run(_check()) == 2


def test_parse_ui_action():
    from src.session import _parse_ui_action
    result = _parse_ui_action('```ui_action\n{"entity":"agent","action":"delete","targets":[]}\n```')
    assert result["entity"] == "agent"


def test_parse_ui_action_none():
    from src.session import _parse_ui_action
    assert _parse_ui_action("just text") is None


def test_find_skill_command(db, user_id):
    from src.session import SessionManager
    sm = SessionManager()
    # Create agent with skill first
    asyncio.run(_collect(sm, user_id, "/create-agent", db))
    asyncio.run(_collect(sm, user_id, "finder-test", db))
    asyncio.run(_collect(sm, user_id, "# Finder", db))
    asyncio.run(_collect(sm, user_id, "review_code", db))
    asyncio.run(_collect(sm, user_id, "Review code for bugs", db))
    asyncio.run(_collect(sm, user_id, "done", db))
    asyncio.run(_collect(sm, user_id, "create", db))
    # Search
    events = asyncio.run(_collect(sm, user_id, "/find-skill", db))
    assert "keyword" in _text(events).lower()
    events = asyncio.run(_collect(sm, user_id, "review", db))
    assert "review_code" in _text(events)


def test_add_skill_search(db, user_id):
    from src.session import SessionManager
    sm = SessionManager()
    # Create agent with a skill
    asyncio.run(_collect(sm, user_id, "/create-agent", db))
    asyncio.run(_collect(sm, user_id, "search-host", db))
    asyncio.run(_collect(sm, user_id, "# Host", db))
    asyncio.run(_collect(sm, user_id, "ping_check", db))
    asyncio.run(_collect(sm, user_id, "Ping check tool", db))
    asyncio.run(_collect(sm, user_id, "done", db))
    asyncio.run(_collect(sm, user_id, "create", db))
    # Create second agent to add skill to
    asyncio.run(_collect(sm, user_id, "/create-agent", db))
    asyncio.run(_collect(sm, user_id, "search-target", db))
    asyncio.run(_collect(sm, user_id, "# Target", db))
    asyncio.run(_collect(sm, user_id, "done", db))
    asyncio.run(_collect(sm, user_id, "create", db))
    # Add skill via search
    asyncio.run(_collect(sm, user_id, "/add-skill", db))
    asyncio.run(_collect(sm, user_id, "search-target", db))
    events = asyncio.run(_collect(sm, user_id, "search ping", db))
    assert "ping_check" in _text(events)
    # Select it
    events = asyncio.run(_collect(sm, user_id, "1", db))
    assert "added" in _text(events).lower()


def test_find_skill_cancel(db, user_id):
    from src.session import SessionManager
    sm = SessionManager()
    asyncio.run(_collect(sm, user_id, "/find-skill", db))
    events = asyncio.run(_collect(sm, user_id, "cancel", db))
    assert "cancelled" in _text(events).lower()


def test_find_skill_no_results(db, user_id):
    from src.session import SessionManager
    sm = SessionManager()
    asyncio.run(_collect(sm, user_id, "/find-skill", db))
    events = asyncio.run(_collect(sm, user_id, "zzz_nonexistent_zzz", db))
    assert "no skills found" in _text(events).lower()


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


def test_slash_command_routes_to_sdk_when_available(monkeypatch):
    """Slash commands should also go through SDK when API key is set."""
    from src.session import _should_use_sdk

    session = {"user_id": "u1"}

    # Mock SDK as available
    monkeypatch.setattr("src.session._should_use_sdk.__module__", "src.session")
    import src.claude_adapter
    monkeypatch.setattr(src.claude_adapter, "is_sdk_available", lambda: True)

    # Slash commands should now return True (not be bypassed)
    assert _should_use_sdk("/list-agents", session) is True
    assert _should_use_sdk("/create-agent", session) is True
    assert _should_use_sdk("/export-agent", session) is True

    # Natural language should also return True
    assert _should_use_sdk("列出所有agent", session) is True

    # But pending flows should still return False
    session_with_pending = {"user_id": "u1", "_pending_create": {"step": "name"}}
    assert _should_use_sdk("/list-agents", session_with_pending) is False
