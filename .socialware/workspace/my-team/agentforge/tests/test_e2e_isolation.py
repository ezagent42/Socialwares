"""E2E: User isolation — users cannot see or modify each other's agents."""
import pytest
import asyncio

from src.db import Database
from src.crud.agent_crud import create_agent, list_agents, delete_agent
from src.seed import seed_example_agent


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    asyncio.run(database.init())
    return database


@pytest.fixture
def two_users(db):
    async def _setup():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('ua', 1, 'user_a')")
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('ub', 2, 'user_b')")
        await conn.commit()
        await conn.close()
    asyncio.run(_setup())
    return "ua", "ub"


def test_user_a_cannot_see_user_b_agents(db, two_users):
    ua, ub = two_users

    async def _run():
        await create_agent(db, ua, "secret", "", "# Secret")
        agents = await list_agents(db, ub)
        user_agents = [a for a in agents if not a.get("is_example")]
        assert len(user_agents) == 0

    asyncio.run(_run())


def test_user_b_cannot_delete_user_a_agent(db, two_users):
    ua, ub = two_users

    async def _run():
        agent = await create_agent(db, ua, "mine", "", "# Mine")
        with pytest.raises(ValueError):
            await delete_agent(db, ub, agent["id"])

    asyncio.run(_run())


def test_example_agent_visible_to_all(db, two_users):
    ua, ub = two_users

    async def _run():
        await seed_example_agent(db)
        agents_a = await list_agents(db, ua)
        agents_b = await list_agents(db, ub)
        assert any(a.get("is_example") for a in agents_a)
        assert any(a.get("is_example") for a in agents_b)

    asyncio.run(_run())
