import pytest
import asyncio
import yaml
from pathlib import Path


@pytest.fixture
def db(tmp_path):
    from src.db import Database
    database = Database(tmp_path / "test.db")
    asyncio.run(database.init())
    return database


@pytest.fixture
def agent_id(db):
    async def _setup():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('u1', 1, 'test')")
        await conn.execute("INSERT INTO agents (id, user_id, name, description, role_md) VALUES ('a1', 'u1', 'test-agent', 'A test', '# Test Agent\nYou test things.')")
        await conn.execute("INSERT INTO skills (id, agent_id, name, description, skill_md) VALUES ('s1', 'a1', 'check', 'Check stuff', '# Check\nDo check.')")
        await conn.commit()
        await conn.close()
        return "a1"
    return asyncio.run(_setup())


def test_export_gitagent(db, agent_id, tmp_path):
    from src.crud.export import export_agent
    result = asyncio.run(export_agent(db, agent_id, tmp_path / "out", format="gitagent"))
    assert (tmp_path / "out" / "agent.yaml").exists()
    assert (tmp_path / "out" / "SOUL.md").exists()
    assert (tmp_path / "out" / "skills" / "check" / "SKILL.md").exists()
    assert result["format"] == "gitagent"
    # Verify agent.yaml content
    data = yaml.safe_load((tmp_path / "out" / "agent.yaml").read_text())
    assert data["name"] == "test-agent"
    assert "check" in data["skills"]


def test_export_claude_code(db, agent_id, tmp_path):
    from src.crud.export import export_agent
    result = asyncio.run(export_agent(db, agent_id, tmp_path / "out", format="claude-code"))
    assert (tmp_path / "out" / "CLAUDE.md").exists()
    assert (tmp_path / "out" / ".claude" / "skills" / "check" / "SKILL.md").exists()
    claude_md = (tmp_path / "out" / "CLAUDE.md").read_text()
    assert "Test Agent" in claude_md


def test_export_codex(db, agent_id, tmp_path):
    from src.crud.export import export_agent
    result = asyncio.run(export_agent(db, agent_id, tmp_path / "out", format="codex"))
    assert (tmp_path / "out" / "AGENTS.md").exists()
    assert (tmp_path / "out" / ".agents" / "skills" / "check" / "SKILL.md").exists()


def test_export_cursor(db, agent_id, tmp_path):
    from src.crud.export import export_agent
    result = asyncio.run(export_agent(db, agent_id, tmp_path / "out", format="cursor"))
    assert (tmp_path / "out" / ".cursor" / "rules").exists()
    rules = (tmp_path / "out" / ".cursor" / "rules").read_text()
    assert "Test Agent" in rules
    assert "check" in rules


def test_export_socialwares(db, agent_id, tmp_path):
    from src.crud.export import export_agent
    result = asyncio.run(export_agent(db, agent_id, tmp_path / "out", format="socialwares"))
    assert (tmp_path / "out" / "agent" / "role" / "default.md").exists()
    assert (tmp_path / "out" / "agent" / "scope" / "scope.md").exists()
    assert (tmp_path / "out" / "agent" / "flow" / "flow.yaml").exists()
    assert (tmp_path / "out" / "agent" / "flow" / "check" / "SKILL.md").exists()


def test_export_unknown_format(db, agent_id, tmp_path):
    from src.crud.export import export_agent
    with pytest.raises(ValueError, match="Unknown format"):
        asyncio.run(export_agent(db, agent_id, tmp_path / "out", format="unknown"))


def test_export_zip(db, agent_id):
    from src.crud.export import export_agent_zip
    zip_path, name = asyncio.run(export_agent_zip(db, agent_id, format="gitagent"))
    assert zip_path.exists()
    assert name == "test-agent"
    assert zip_path.suffix == ".zip"
