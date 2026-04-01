# tests/test_chat_api.py
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


def test_session_manager_send_text(db, user_id):
    """Session manager returns text events for a simple message."""
    from src.session import SessionManager
    sm = SessionManager()
    events = asyncio.run(_collect_events(sm, user_id, "hello", db))
    event_types = [e["event"] for e in events]
    assert "text" in event_types
    assert "done" in event_types


def test_create_wizard_full_flow(db, user_id):
    """Full create wizard: name → model → scope → done roles → done skills → done commitments → create."""
    from src.session import SessionManager
    sm = SessionManager()

    # Step 1: start wizard
    events = asyncio.run(_collect_events(sm, user_id, "/create-agent", db))
    text = _get_text(events)
    assert "Step 1" in text
    assert "name" in text.lower()

    # Step 2: name → asks for model
    events = asyncio.run(_collect_events(sm, user_id, "test-app", db))
    text = _get_text(events)
    assert "Step 2" in text
    assert "model" in text.lower()

    # Step 3: model → asks for scope
    events = asyncio.run(_collect_events(sm, user_id, "claude", db))
    text = _get_text(events)
    assert "Step 3" in text

    # Step 4: scope → asks for roles
    events = asyncio.run(_collect_events(sm, user_id, "Task management system", db))
    text = _get_text(events)
    assert "Step 4" in text
    assert "role" in text.lower()

    # Step 5: skip roles → asks for skills
    events = asyncio.run(_collect_events(sm, user_id, "done", db))
    text = _get_text(events)
    assert "Step 5" in text
    assert "skill" in text.lower()

    # Step 6: skip skills → asks for commitments
    events = asyncio.run(_collect_events(sm, user_id, "done", db))
    text = _get_text(events)
    assert "Step 6" in text

    # Step 7: skip commitments → shows preview
    events = asyncio.run(_collect_events(sm, user_id, "done", db))
    text = _get_text(events)
    assert "Step 7" in text
    assert "test-app" in text
    assert "claude" in text

    # Confirm creation
    events = asyncio.run(_collect_events(sm, user_id, "create", db))
    text = _get_text(events)
    assert "successfully" in text.lower() or "created" in text.lower()
    structured = _get_structured(events)
    assert structured is not None
    assert structured["type"] == "agent"
    assert structured["action"] == "created"
    assert structured["data"]["name"] == "test-app"


def test_create_wizard_with_roles_and_skills(db, user_id):
    """Wizard with extra role and skill."""
    from src.session import SessionManager
    sm = SessionManager()

    asyncio.run(_collect_events(sm, user_id, "/create-agent", db))
    asyncio.run(_collect_events(sm, user_id, "my-agent", db))       # name
    asyncio.run(_collect_events(sm, user_id, "1", db))              # model (claude)
    asyncio.run(_collect_events(sm, user_id, "skip", db))           # scope
    asyncio.run(_collect_events(sm, user_id, "reviewer", db))       # add role
    asyncio.run(_collect_events(sm, user_id, "Reviews tasks", db))  # role desc
    asyncio.run(_collect_events(sm, user_id, "done", db))           # done roles
    asyncio.run(_collect_events(sm, user_id, "create_task", db))    # add skill
    asyncio.run(_collect_events(sm, user_id, "Creates new tasks", db))  # skill desc
    # 2 roles exist (default + reviewer), so it asks which roles
    asyncio.run(_collect_events(sm, user_id, "all", db))            # assign to all roles
    asyncio.run(_collect_events(sm, user_id, "done", db))           # done skills
    asyncio.run(_collect_events(sm, user_id, "done", db))           # done commitments

    # Preview should show role + skill
    events = asyncio.run(_collect_events(sm, user_id, "create", db))
    structured = _get_structured(events)
    assert structured is not None
    assert structured["data"]["name"] == "my-agent"
    roles = structured["data"].get("roles", [])
    assert len(roles) == 2  # default + reviewer
    skills = structured["data"].get("skills", [])
    assert len(skills) == 1  # create_task


def test_create_wizard_cancel(db, user_id):
    """Cancel wizard at any step."""
    from src.session import SessionManager
    sm = SessionManager()

    asyncio.run(_collect_events(sm, user_id, "/create-agent", db))
    events = asyncio.run(_collect_events(sm, user_id, "cancel", db))
    text = _get_text(events)
    assert "cancelled" in text.lower()


def test_natural_language_create_enters_wizard(db, user_id):
    """Natural language '创建一个 xxx Agent' enters wizard at step 2."""
    from src.session import SessionManager
    sm = SessionManager()

    events = asyncio.run(_collect_events(sm, user_id, "创建一个 task-mgr Agent", db))
    text = _get_text(events)
    assert "Step 2" in text  # skipped step 1, pre-filled name
    assert "model" in text.lower()


def test_list_agents_after_wizard(db, user_id):
    """List agents after creating via wizard."""
    from src.session import SessionManager
    sm = SessionManager()

    # Quick create
    asyncio.run(_collect_events(sm, user_id, "/create-agent", db))
    asyncio.run(_collect_events(sm, user_id, "list-test", db))
    asyncio.run(_collect_events(sm, user_id, "claude", db))
    asyncio.run(_collect_events(sm, user_id, "skip", db))
    asyncio.run(_collect_events(sm, user_id, "done", db))
    asyncio.run(_collect_events(sm, user_id, "done", db))
    asyncio.run(_collect_events(sm, user_id, "done", db))
    asyncio.run(_collect_events(sm, user_id, "create", db))

    # List
    events = asyncio.run(_collect_events(sm, user_id, "/list-agents", db))
    structured = _get_structured(events)
    assert structured is not None
    assert structured["action"] == "listed"
    assert len(structured["data"]["agents"]) == 1
    assert structured["data"]["agents"][0]["name"] == "list-test"


def test_session_manager_ui_action_delete(db, user_id):
    """UI action delete triggers confirm_required."""
    from src.session import SessionManager
    sm = SessionManager()
    msg = '```ui_action\n{"entity": "agent", "action": "delete", "targets": [{"id": "a1", "name": "test"}]}\n```'
    events = asyncio.run(_collect_events(sm, user_id, msg, db))
    structured = _get_structured(events)
    assert structured is not None
    assert structured["action"] == "confirm_required"


def test_chat_history_saved(db, user_id):
    """Messages are saved to chat_history table."""
    from src.session import SessionManager
    sm = SessionManager()
    asyncio.run(_collect_events(sm, user_id, "hello", db))
    async def _check():
        conn = await db.connect()
        cursor = await conn.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ?", (user_id,))
        count = (await cursor.fetchone())[0]
        await conn.close()
        return count
    count = asyncio.run(_check())
    assert count == 2  # user message + assistant message


def test_parse_ui_action():
    """_parse_ui_action extracts JSON from ui_action block."""
    from src.session import _parse_ui_action
    msg = '```ui_action\n{"entity": "agent", "action": "delete", "targets": []}\n```'
    result = _parse_ui_action(msg)
    assert result["entity"] == "agent"
    assert result["action"] == "delete"


def test_parse_ui_action_no_block():
    """_parse_ui_action returns None for plain text."""
    from src.session import _parse_ui_action
    assert _parse_ui_action("just a normal message") is None


# ===== Helpers =====

async def _collect_events(sm, user_id, message, db):
    events = []
    async for event in sm.send(user_id, message, db):
        events.append(event)
    return events


def _get_text(events):
    for e in events:
        if e["event"] == "text":
            return json.loads(e["data"]).get("content", "")
    return ""


def _get_structured(events):
    for e in events:
        if e["event"] == "structured":
            return json.loads(e["data"])
    return None
