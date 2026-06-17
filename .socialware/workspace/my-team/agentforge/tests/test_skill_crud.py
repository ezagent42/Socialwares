import pytest
import asyncio


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
        await conn.execute("INSERT INTO agents (id, user_id, name, role_md) VALUES ('a1', 'u1', 'test-app', '# Test')")
        await conn.commit()
        await conn.close()
        return "a1"
    return asyncio.run(_setup())


def test_create_skill(db, agent_id):
    from src.crud.skill_crud import create_skill
    skill = asyncio.run(create_skill(db, agent_id, "check", "# Check\nDo check.", "Check stuff"))
    assert skill["name"] == "check"
    assert skill["skill_md"] == "# Check\nDo check."
    assert "roles" not in skill  # no role-based permissions


def test_create_skill_duplicate(db, agent_id):
    from src.crud.skill_crud import create_skill
    asyncio.run(create_skill(db, agent_id, "dup", "# Dup", ""))
    with pytest.raises(ValueError, match="already exists"):
        asyncio.run(create_skill(db, agent_id, "dup", "# Dup2", ""))


def test_list_skills(db, agent_id):
    from src.crud.skill_crud import create_skill, list_skills
    asyncio.run(create_skill(db, agent_id, "s1", "# S1", ""))
    asyncio.run(create_skill(db, agent_id, "s2", "# S2", ""))
    skills = asyncio.run(list_skills(db, agent_id))
    assert len(skills) == 2


def test_update_skill(db, agent_id):
    from src.crud.skill_crud import create_skill, update_skill
    s = asyncio.run(create_skill(db, agent_id, "upd", "# Old", ""))
    updated = asyncio.run(update_skill(db, s["id"], skill_md="# New"))
    assert updated["skill_md"] == "# New"


def test_delete_skill(db, agent_id):
    from src.crud.skill_crud import create_skill, delete_skill, list_skills
    s = asyncio.run(create_skill(db, agent_id, "del", "# Del", ""))
    asyncio.run(delete_skill(db, s["id"]))
    assert len(asyncio.run(list_skills(db, agent_id))) == 0
