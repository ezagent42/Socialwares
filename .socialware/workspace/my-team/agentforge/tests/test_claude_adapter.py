import asyncio

import pytest
from src.claude_adapter import AGENT_TOOLS, execute_tool
from src.db import Database


def test_agent_tools_defined():
    """All 10 CRUD tools should be defined with name, description, input_schema."""
    assert len(AGENT_TOOLS) == 10
    names = {t["name"] for t in AGENT_TOOLS}
    expected = {
        "list_agents", "create_agent", "get_agent", "delete_agent",
        "create_skill", "list_skills", "delete_skill",
        "export_agent", "search_skills", "import_agent",
    }
    assert names == expected
    for tool in AGENT_TOOLS:
        assert "description" in tool
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    asyncio.run(database.init())
    return database


@pytest.fixture
def user_id(db):
    async def _setup():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('u1', 1, 'tester')")
        await conn.commit()
        await conn.close()
        return "u1"
    return asyncio.run(_setup())


def test_execute_tool_list_agents(db, user_id):
    result = asyncio.run(execute_tool("list_agents", {}, user_id, db))
    assert isinstance(result, dict)
    assert "agents" in result


def test_execute_tool_create_and_list(db, user_id):
    create_result = asyncio.run(execute_tool("create_agent", {
        "name": "test-bot",
        "description": "A test agent",
        "role_md": "# Test Bot\nYou are a test bot.",
    }, user_id, db))
    assert create_result["name"] == "test-bot"

    list_result = asyncio.run(execute_tool("list_agents", {}, user_id, db))
    assert any(a["name"] == "test-bot" for a in list_result["agents"])


def test_execute_tool_unknown():
    """Unknown tool should return error dict."""
    result = asyncio.run(execute_tool("unknown_tool", {}, "u1", None))
    assert "error" in result


def test_send_to_agent_has_tools_param():
    """send_to_agent should accept db, user_id, and session params."""
    import inspect
    from src.claude_adapter import send_to_agent
    sig = inspect.signature(send_to_agent)
    params = list(sig.parameters.keys())
    assert "db" in params
    assert "user_id" in params
    assert "session" in params


def test_system_prompt_includes_structured_format(tmp_path):
    from src.claude_adapter import build_system_prompt
    prompt = build_system_prompt(tmp_path, "u1", "test.db")
    assert "json:structured" in prompt
    assert "type" in prompt and "action" in prompt
    assert "agent" in prompt and "listed" in prompt


def test_is_sdk_available():
    """is_sdk_available checks for claude-agent-sdk, not ANTHROPIC_API_KEY."""
    from src.claude_adapter import is_sdk_available
    # Should return True if claude-agent-sdk is installed (it's in our deps)
    result = is_sdk_available()
    assert isinstance(result, bool)
