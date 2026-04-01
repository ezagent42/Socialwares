# tests/test_agent_crud.py
import pytest
import asyncio


@pytest.fixture
def db(tmp_path):
    from src.db import Database
    database = Database(tmp_path / "test.db")
    asyncio.run(database.init())
    return database


@pytest.fixture
def user_id(db):
    """Create a test user and return user_id."""
    async def _create():
        conn = await db.connect()
        await conn.execute(
            "INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)",
            ("u1", 12345, "testuser")
        )
        await conn.commit()
        await conn.close()
        return "u1"
    return asyncio.run(_create())


def test_create_agent(db, user_id):
    from src.crud.agent_crud import create_agent
    agent = asyncio.run(create_agent(db, user_id, "task-manager", "Manage tasks"))
    assert agent["name"] == "task-manager"
    assert agent["description"] == "Manage tasks"
    assert "id" in agent
    assert len(agent["roles"]) == 1
    assert agent["roles"][0]["name"] == "default"
    assert "scope" in agent


def test_create_agent_duplicate_name(db, user_id):
    from src.crud.agent_crud import create_agent
    asyncio.run(create_agent(db, user_id, "dup", "first"))
    with pytest.raises(ValueError, match="already exists"):
        asyncio.run(create_agent(db, user_id, "dup", "second"))


def test_list_agents(db, user_id):
    from src.crud.agent_crud import create_agent, list_agents
    asyncio.run(create_agent(db, user_id, "a1", ""))
    asyncio.run(create_agent(db, user_id, "a2", ""))
    agents = asyncio.run(list_agents(db, user_id))
    assert len(agents) == 2


def test_get_agent(db, user_id):
    from src.crud.agent_crud import create_agent, get_agent
    created = asyncio.run(create_agent(db, user_id, "x", "desc"))
    agent = asyncio.run(get_agent(db, user_id, created["id"]))
    assert agent["name"] == "x"
    assert "roles" in agent
    assert "skills" in agent


def test_delete_agent(db, user_id):
    from src.crud.agent_crud import create_agent, delete_agent, list_agents
    created = asyncio.run(create_agent(db, user_id, "del-me", ""))
    asyncio.run(delete_agent(db, user_id, created["id"]))
    agents = asyncio.run(list_agents(db, user_id))
    assert len(agents) == 0


def test_user_isolation(db):
    """User A cannot see User B's agents."""
    from src.crud.agent_crud import create_agent, list_agents
    async def _setup():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)", ("ua", 1, "alice"))
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)", ("ub", 2, "bob"))
        await conn.commit()
        await conn.close()
    asyncio.run(_setup())
    asyncio.run(create_agent(db, "ua", "alice-agent", ""))
    asyncio.run(create_agent(db, "ub", "bob-agent", ""))
    alice_agents = asyncio.run(list_agents(db, "ua"))
    bob_agents = asyncio.run(list_agents(db, "ub"))
    assert len(alice_agents) == 1
    assert alice_agents[0]["name"] == "alice-agent"
    assert len(bob_agents) == 1
    assert bob_agents[0]["name"] == "bob-agent"
