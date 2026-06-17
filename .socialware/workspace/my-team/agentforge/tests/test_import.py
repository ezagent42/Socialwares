import pytest
import asyncio
from pathlib import Path


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


def _make_gitagent(path):
    path.mkdir(parents=True, exist_ok=True)
    import yaml
    (path / "agent.yaml").write_text(yaml.dump({"name": "test-ga", "version": "1.0.0", "description": "GA test", "skills": ["check"]}))
    (path / "SOUL.md").write_text("# Test GA\nYou test.")
    (path / "skills" / "check").mkdir(parents=True)
    (path / "skills" / "check" / "SKILL.md").write_text("# Check\nDo check.")


def _make_claude_code(path):
    path.mkdir(parents=True, exist_ok=True)
    (path / "CLAUDE.md").write_text("# Claude Test\nYou help.")
    (path / ".claude" / "skills" / "help").mkdir(parents=True)
    (path / ".claude" / "skills" / "help" / "SKILL.md").write_text("# Help\nHelp user.")


def _make_cursor(path):
    (path / ".cursor").mkdir(parents=True)
    (path / ".cursor" / "rules").write_text("# Cursor Test\nFollow these rules.")


def test_import_gitagent(db, user_id, tmp_path):
    from src.crud.import_agent import import_agent
    _make_gitagent(tmp_path / "src")
    agent = asyncio.run(import_agent(db, user_id, tmp_path / "src"))
    assert agent["name"] == "test-ga"
    assert "Test GA" in agent["role_md"]
    assert len(agent["skills"]) == 1
    assert agent["format"] == "gitagent"


def test_import_claude_code(db, user_id, tmp_path):
    from src.crud.import_agent import import_agent
    _make_claude_code(tmp_path / "src")
    agent = asyncio.run(import_agent(db, user_id, tmp_path / "src"))
    assert "Claude" in agent["name"] or "claude" in agent["name"].lower()
    assert len(agent["skills"]) == 1
    assert agent["format"] == "claude-code"


def test_import_cursor(db, user_id, tmp_path):
    from src.crud.import_agent import import_agent
    _make_cursor(tmp_path / "src")
    agent = asyncio.run(import_agent(db, user_id, tmp_path / "src"))
    assert agent["format"] == "cursor"
    assert "Cursor Test" in agent["role_md"]


def test_import_roundtrip_gitagent(db, user_id, tmp_path):
    """Export as gitagent -> import -> verify data matches."""
    from src.crud.agent_crud import create_agent
    from src.crud.skill_crud import create_skill
    from src.crud.export import export_agent
    from src.crud.import_agent import import_agent

    orig = asyncio.run(create_agent(db, user_id, "roundtrip", "RT test", "# RT\nRoundtrip."))
    asyncio.run(create_skill(db, orig["id"], "ping", "# Ping\nPing.", "Ping"))
    asyncio.run(export_agent(db, orig["id"], tmp_path / "exported", format="gitagent"))

    # Import as different user
    async def _add_user():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('u2', 2, 'other')")
        await conn.commit()
        await conn.close()
    asyncio.run(_add_user())

    imported = asyncio.run(import_agent(db, "u2", tmp_path / "exported"))
    assert imported["name"] == "roundtrip"
    assert "RT" in imported["role_md"]
    assert len(imported["skills"]) == 1


def test_import_name_conflict(db, user_id, tmp_path):
    from src.crud.agent_crud import create_agent
    from src.crud.import_agent import import_agent
    asyncio.run(create_agent(db, user_id, "test-ga", "", "# Existing"))
    _make_gitagent(tmp_path / "src")
    with pytest.raises(ValueError, match="already exists"):
        asyncio.run(import_agent(db, user_id, tmp_path / "src"))


def test_import_unknown_format(db, user_id, tmp_path):
    from src.crud.import_agent import import_agent
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError, match="Unknown format"):
        asyncio.run(import_agent(db, user_id, tmp_path / "empty"))
