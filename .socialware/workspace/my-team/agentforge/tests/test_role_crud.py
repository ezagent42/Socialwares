# tests/test_role_crud.py
import pytest
import asyncio


@pytest.fixture
def db(tmp_path):
    from src.db import Database
    database = Database(tmp_path / "test.db")
    asyncio.run(database.init())
    return database


@pytest.fixture
def agent(db):
    """Create a test user and agent, return (db, agent_dict)."""
    async def _setup():
        conn = await db.connect()
        await conn.execute(
            "INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)",
            ("u1", 12345, "testuser"),
        )
        await conn.commit()
        await conn.close()
    asyncio.run(_setup())

    from src.crud.agent_crud import create_agent
    return asyncio.run(create_agent(db, "u1", "test-agent", "A test agent"))


def test_create_role(db, agent):
    from src.crud.role_crud import create_role
    role = asyncio.run(create_role(db, agent["id"], "admin", "# Admin role"))
    assert role["name"] == "admin"
    assert "id" in role


def test_list_roles(db, agent):
    from src.crud.role_crud import create_role, list_roles
    asyncio.run(create_role(db, agent["id"], "extra", "# Extra"))
    roles = asyncio.run(list_roles(db, agent["id"]))
    assert len(roles) == 2


def test_update_role(db, agent):
    from src.crud.role_crud import create_role, update_role
    role = asyncio.run(create_role(db, agent["id"], "updatable", "# Old"))
    updated = asyncio.run(update_role(db, role["id"], "# New soul"))
    assert updated["soul_md"] == "# New soul"


def test_delete_role_prevents_last(db, agent):
    from src.crud.role_crud import list_roles, delete_role
    roles = asyncio.run(list_roles(db, agent["id"]))
    assert len(roles) == 1
    with pytest.raises(ValueError, match="at least one"):
        asyncio.run(delete_role(db, roles[0]["id"]))
