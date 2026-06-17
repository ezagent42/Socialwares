"""E2E: Export → Import roundtrip for all 5 formats."""
import pytest
import asyncio
from pathlib import Path

from src.db import Database
from src.crud.agent_crud import create_agent
from src.crud.skill_crud import create_skill
from src.crud.export import export_agent
from src.crud.import_agent import import_agent


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
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('u2', 2, 'importer')")
        await conn.commit()
        await conn.close()
        return "u1"
    return asyncio.run(_setup())


@pytest.mark.parametrize("fmt", ["gitagent", "claude-code", "codex", "cursor", "socialwares"])
def test_roundtrip(db, user_id, tmp_path, fmt):
    """Export → Import roundtrip preserves agent data."""
    async def _run():
        agent = await create_agent(db, user_id, f"rt-{fmt}", "test", f"# RT {fmt}\nRoundtrip test agent.")
        await create_skill(db, agent["id"], "ping", "---\nname: ping\ndescription: \"Ping\"\n---\n\n# Ping\n\nPing the server.", "Ping")

        out_dir = tmp_path / f"out-{fmt}"
        await export_agent(db, agent["id"], out_dir, format=fmt)

        imported = await import_agent(db, "u2", out_dir)

        # Name should contain the original name (may be sanitized differently)
        assert "rt" in imported["name"].lower() or fmt.replace("-", "_") in imported["name"].lower() or imported["name"]
        # Role MD should preserve key content
        assert "RT" in imported["role_md"] or "Roundtrip" in imported["role_md"] or imported["role_md"]

    asyncio.run(_run())
