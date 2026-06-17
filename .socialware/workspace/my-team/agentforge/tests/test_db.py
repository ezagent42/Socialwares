import pytest
import asyncio


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def db(db_path):
    from src.db import Database
    database = Database(db_path)
    asyncio.run(database.init())
    return database


def test_database_creates_tables(db, db_path):
    assert db_path.exists()
    tables = asyncio.run(db.list_tables())
    expected = {"users", "sessions", "agents", "skills", "chat_history"}
    assert set(tables) == expected


def test_database_no_old_tables(db):
    tables = asyncio.run(db.list_tables())
    for old in ["roles", "scopes", "commitments", "skill_roles"]:
        assert old not in tables


def test_agents_has_role_md(db):
    async def _check():
        conn = await db.connect()
        cursor = await conn.execute("PRAGMA table_info(agents)")
        columns = {row[1] for row in await cursor.fetchall()}
        await conn.close()
        return columns
    columns = asyncio.run(_check())
    assert "role_md" in columns
    assert "model" not in columns


def test_database_is_idempotent(db):
    asyncio.run(db.init())
