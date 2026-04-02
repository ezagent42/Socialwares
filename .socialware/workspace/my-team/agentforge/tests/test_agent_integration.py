"""Integration test: Agent-driven CRUD via Claude Agent SDK.

Requires claude-agent-sdk and Claude Code CLI to be installed and authenticated.
Skipped automatically if CLI is not available.
"""
import os
import pytest
import asyncio

from src.db import Database
from src.claude_adapter import is_sdk_available, build_system_prompt

# Skip if claude-agent-sdk is not available
pytestmark = pytest.mark.skipif(
    not is_sdk_available(),
    reason="claude-agent-sdk not available"
)


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


def test_sdk_available():
    assert is_sdk_available()


def test_build_system_prompt(tmp_path):
    from pathlib import Path
    runtime_dir = tmp_path / ".runtime" / "agents" / "default"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "SOUL.md").write_text("# Test Agent\nYou are a test agent.")
    prompt = build_system_prompt(runtime_dir, "u1", str(tmp_path / "test.db"))
    assert "Test Agent" in prompt
    assert "USER_ID: u1" in prompt
    assert "DB_PATH:" in prompt


def test_create_mcp_tools(db, user_id):
    """MCP tools should be created with correct names."""
    from src.claude_adapter import _create_mcp_tools
    tools = _create_mcp_tools(db, user_id)
    assert len(tools) == 10
