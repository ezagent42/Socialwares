import pytest
import asyncio
from pathlib import Path


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
    """Database.init() creates all required tables."""
    assert db_path.exists()
    tables = asyncio.run(db.list_tables())
    expected = {"users", "sessions", "agents", "roles", "skills", "skill_roles", "scopes", "commitments", "chat_history"}
    assert set(tables) == expected


def test_database_is_idempotent(db):
    """Calling init() twice does not raise."""
    asyncio.run(db.init())
