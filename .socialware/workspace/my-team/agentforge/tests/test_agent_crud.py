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
    async def _create():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)", ("u1", 12345, "testuser"))
        await conn.commit()
        await conn.close()
        return "u1"
    return asyncio.run(_create())


def test_create_agent(db, user_id):
    from src.crud.agent_crud import create_agent
    agent = asyncio.run(create_agent(db, user_id, "test-app", "A test agent", "# Test\nYou test things."))
    assert agent["name"] == "test-app"
    assert agent["role_md"] == "# Test\nYou test things."
    assert "model" not in agent
    assert agent["skills"] == []


def test_create_agent_duplicate(db, user_id):
    from src.crud.agent_crud import create_agent
    asyncio.run(create_agent(db, user_id, "dup", "", "# Dup"))
    with pytest.raises(ValueError, match="already exists"):
        asyncio.run(create_agent(db, user_id, "dup", "", "# Dup"))


def test_list_agents(db, user_id):
    from src.crud.agent_crud import create_agent, list_agents
    asyncio.run(create_agent(db, user_id, "a1", "", "# A1"))
    asyncio.run(create_agent(db, user_id, "a2", "", "# A2"))
    agents = asyncio.run(list_agents(db, user_id))
    assert len(agents) == 2


def test_get_agent(db, user_id):
    from src.crud.agent_crud import create_agent, get_agent
    created = asyncio.run(create_agent(db, user_id, "x", "desc", "# X"))
    agent = asyncio.run(get_agent(db, user_id, created["id"]))
    assert agent["name"] == "x"
    assert agent["role_md"] == "# X"
    assert "skills" in agent


def test_update_agent(db, user_id):
    from src.crud.agent_crud import create_agent, update_agent
    created = asyncio.run(create_agent(db, user_id, "upd", "", "# Old"))
    updated = asyncio.run(update_agent(db, user_id, created["id"], role_md="# New"))
    assert updated["role_md"] == "# New"


def test_delete_agent(db, user_id):
    from src.crud.agent_crud import create_agent, delete_agent, list_agents
    created = asyncio.run(create_agent(db, user_id, "del-me", "", "# Del"))
    asyncio.run(delete_agent(db, user_id, created["id"]))
    agents = asyncio.run(list_agents(db, user_id))
    assert len(agents) == 0


def test_user_isolation(db):
    from src.crud.agent_crud import create_agent, list_agents
    async def _setup():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)", ("ua", 1, "alice"))
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)", ("ub", 2, "bob"))
        await conn.commit()
        await conn.close()
    asyncio.run(_setup())
    asyncio.run(create_agent(db, "ua", "alice-agent", "", "# Alice"))
    asyncio.run(create_agent(db, "ub", "bob-agent", "", "# Bob"))
    assert len(asyncio.run(list_agents(db, "ua"))) == 1
    assert len(asyncio.run(list_agents(db, "ub"))) == 1
