# tests/test_skill_crud.py
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
    """Create a test user and agent, return agent dict (includes default role)."""
    async def _setup():
        conn = await db.connect()
        await conn.execute(
            "INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)",
            ("u1", 12345, "testuser"),
        )
        await conn.commit()
        await conn.close()

        from src.crud.agent_crud import create_agent
        return await create_agent(db, "u1", "test-agent", "A test agent")

    return asyncio.run(_setup())


def test_create_skill(db, agent):
    from src.crud.skill_crud import create_skill
    role_id = agent["roles"][0]["id"]
    skill = asyncio.run(create_skill(
        db, agent["id"], "greet", "# Greet\nSay hello.", [role_id],
        description="Greeting skill",
    ))
    assert skill["name"] == "greet"
    assert skill["description"] == "Greeting skill"
    assert len(skill["roles"]) == 1
    assert skill["roles"][0]["id"] == role_id
    assert skill["roles"][0]["name"] == "default"
    assert skill["skill_md"] == "# Greet\nSay hello."


def test_create_skill_requires_role(db, agent):
    from src.crud.skill_crud import create_skill
    with pytest.raises(ValueError, match="At least one role_id"):
        asyncio.run(create_skill(
            db, agent["id"], "no-role", "# No role", [],
        ))


def test_list_skills_with_roles(db, agent):
    from src.crud.skill_crud import create_skill, list_skills
    role_id = agent["roles"][0]["id"]
    asyncio.run(create_skill(db, agent["id"], "skill-a", "# A", [role_id]))
    asyncio.run(create_skill(db, agent["id"], "skill-b", "# B", [role_id]))
    skills = asyncio.run(list_skills(db, agent["id"]))
    assert len(skills) == 2
    names = {s["name"] for s in skills}
    assert names == {"skill-a", "skill-b"}
    for s in skills:
        assert len(s["roles"]) == 1
        assert s["roles"][0]["name"] == "default"


def test_update_skill_content(db, agent):
    from src.crud.skill_crud import create_skill, update_skill
    role_id = agent["roles"][0]["id"]
    skill = asyncio.run(create_skill(db, agent["id"], "updatable", "# Old", [role_id]))
    updated = asyncio.run(update_skill(db, skill["id"], skill_md="# New content"))
    assert updated["skill_md"] == "# New content"
    assert updated["name"] == "updatable"
    # Roles should be unchanged
    assert len(updated["roles"]) == 1


def test_update_skill_roles(db, agent):
    from src.crud.skill_crud import create_skill, update_skill
    role_id = agent["roles"][0]["id"]

    # Create a second role
    async def _add_role():
        conn = await db.connect()
        import uuid
        r2 = uuid.uuid4().hex[:12]
        await conn.execute(
            "INSERT INTO roles (id, agent_id, name, soul_md) VALUES (?, ?, ?, ?)",
            (r2, agent["id"], "admin", "# Admin role"),
        )
        await conn.commit()
        await conn.close()
        return r2

    role2_id = asyncio.run(_add_role())

    skill = asyncio.run(create_skill(db, agent["id"], "multi", "# Multi", [role_id]))
    assert len(skill["roles"]) == 1

    updated = asyncio.run(update_skill(db, skill["id"], role_ids=[role_id, role2_id]))
    assert len(updated["roles"]) == 2
    role_names = {r["name"] for r in updated["roles"]}
    assert role_names == {"default", "admin"}

    # Reassign to only the new role
    updated2 = asyncio.run(update_skill(db, skill["id"], role_ids=[role2_id]))
    assert len(updated2["roles"]) == 1
    assert updated2["roles"][0]["name"] == "admin"


def test_delete_skill(db, agent):
    from src.crud.skill_crud import create_skill, delete_skill, list_skills
    role_id = agent["roles"][0]["id"]
    skill = asyncio.run(create_skill(db, agent["id"], "temp", "# Temp", [role_id]))
    result = asyncio.run(delete_skill(db, skill["id"]))
    assert result["name"] == "temp"
    skills = asyncio.run(list_skills(db, agent["id"]))
    assert len(skills) == 0
