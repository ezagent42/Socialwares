"""Integration test: Agent tool use — full CRUD lifecycle via execute_tool."""
import asyncio
import json
import pytest
from src.db import Database
from src.claude_adapter import execute_tool, AGENT_TOOLS


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


def test_tool_execute_create_get_delete(db, user_id):
    """Full lifecycle: create → get → delete via execute_tool."""
    # Create
    agent = asyncio.run(execute_tool("create_agent", {
        "name": "lifecycle-bot",
        "description": "test lifecycle",
        "role_md": "# Lifecycle Bot",
    }, user_id, db))
    assert agent["name"] == "lifecycle-bot"
    agent_id = agent["id"]

    # Get
    detail = asyncio.run(execute_tool("get_agent", {"agent_id": agent_id}, user_id, db))
    assert detail["name"] == "lifecycle-bot"
    assert detail["role_md"] == "# Lifecycle Bot"

    # Create skill
    skill = asyncio.run(execute_tool("create_skill", {
        "agent_id": agent_id,
        "name": "greet",
        "description": "Greeting skill",
        "skill_md": "# Greet\nSay hello.",
    }, user_id, db))
    assert skill["name"] == "greet"

    # List skills
    skills = asyncio.run(execute_tool("list_skills", {"agent_id": agent_id}, user_id, db))
    assert len(skills["skills"]) == 1

    # Delete skill
    del_skill = asyncio.run(execute_tool("delete_skill", {"skill_id": skill["id"]}, user_id, db))
    assert del_skill["name"] == "greet"

    # Delete agent
    deleted = asyncio.run(execute_tool("delete_agent", {"agent_id": agent_id}, user_id, db))
    assert deleted["name"] == "lifecycle-bot"

    # Verify gone
    result = asyncio.run(execute_tool("get_agent", {"agent_id": agent_id}, user_id, db))
    assert "error" in result


def test_tool_execute_search_skills(db, user_id):
    """search_skills tool returns results list."""
    result = asyncio.run(execute_tool("search_skills", {"query": "manage"}, user_id, db))
    assert "results" in result
    assert isinstance(result["results"], list)


def test_tool_execute_export_agent(db, user_id):
    """export_agent tool returns download URL."""
    agent = asyncio.run(execute_tool("create_agent", {
        "name": "export-test",
        "description": "",
        "role_md": "# Export Test",
    }, user_id, db))

    result = asyncio.run(execute_tool("export_agent", {
        "agent_id": agent["id"],
        "format": "gitagent",
    }, user_id, db))
    assert "download_url" in result
    assert "gitagent" in result["download_url"]
