# tests/test_import.py
import asyncio
import pytest
import yaml


@pytest.fixture
def db(tmp_path):
    from src.db import Database
    database = Database(tmp_path / "test.db")
    asyncio.run(database.init())
    return database


@pytest.fixture
def user(db):
    """Create test users u1 and u2."""
    async def _setup():
        conn = await db.connect()
        await conn.execute(
            "INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)",
            ("u1", 12345, "testuser1"),
        )
        await conn.execute(
            "INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)",
            ("u2", 67890, "testuser2"),
        )
        await conn.commit()
        await conn.close()
    asyncio.run(_setup())
    return {"u1": "u1", "u2": "u2"}


@pytest.fixture
def agent_with_skill(db, user):
    """Create an agent with a custom role and skill, return (agent, role, skill)."""
    async def _setup():
        from src.crud.agent_crud import create_agent
        from src.crud.role_crud import create_role
        from src.crud.skill_crud import create_skill

        agent = await create_agent(db, "u1", "test-agent", "A test agent")
        role = await create_role(
            db, agent["id"], "greeter",
            "# Greeter Role\n\nYou greet people warmly.\n",
        )
        default_role_id = agent["roles"][0]["id"]
        skill = await create_skill(
            db, agent["id"], "greet", "# Greet Skill\n\nSay hello to the user.\n",
            [default_role_id, role["id"]],
            description="Greeting skill",
        )
        return agent, role, skill
    return asyncio.run(_setup())


def test_import_from_exported(db, agent_with_skill, user, tmp_path):
    """Roundtrip: create -> export -> import into different user -> verify content match."""
    from src.crud.export import export_agent
    from src.crud.import_agent import import_agent
    from src.crud.role_crud import list_roles
    from src.crud.skill_crud import list_skills
    from src.crud.scope_crud import get_scope
    from src.crud.commitment_crud import get_commitment

    agent, role, skill = agent_with_skill
    export_dir = tmp_path / "exported"

    # Export
    asyncio.run(export_agent(db, agent["id"], export_dir))

    # Import into user u2
    imported = asyncio.run(import_agent(db, "u2", export_dir))

    assert imported["name"] == "test-agent"
    assert imported["id"] != agent["id"]  # different agent record

    # Verify roles match
    orig_roles = asyncio.run(list_roles(db, agent["id"]))
    imp_roles = asyncio.run(list_roles(db, imported["id"]))
    assert len(imp_roles) == len(orig_roles)
    orig_role_names = sorted(r["name"] for r in orig_roles)
    imp_role_names = sorted(r["name"] for r in imp_roles)
    assert imp_role_names == orig_role_names

    # Verify role content matches
    for orig_r in orig_roles:
        matching = [r for r in imp_roles if r["name"] == orig_r["name"]]
        assert len(matching) == 1
        assert matching[0]["soul_md"] == orig_r["soul_md"]

    # Verify skills match
    orig_skills = asyncio.run(list_skills(db, agent["id"]))
    imp_skills = asyncio.run(list_skills(db, imported["id"]))
    assert len(imp_skills) == len(orig_skills)

    for orig_s in orig_skills:
        matching = [s for s in imp_skills if s["name"] == orig_s["name"]]
        assert len(matching) == 1
        assert matching[0]["skill_md"] == orig_s["skill_md"]
        assert matching[0]["description"] == orig_s["description"]
        # Verify skill_roles mapping
        orig_role_names_for_skill = sorted(r["name"] for r in orig_s["roles"])
        imp_role_names_for_skill = sorted(r["name"] for r in matching[0]["roles"])
        assert imp_role_names_for_skill == orig_role_names_for_skill

    # Verify scope matches
    orig_scope = asyncio.run(get_scope(db, agent["id"]))
    imp_scope = asyncio.run(get_scope(db, imported["id"]))
    assert imp_scope["soul_md"] == orig_scope["soul_md"]

    # Verify commitment matches
    orig_commit = asyncio.run(get_commitment(db, agent["id"]))
    imp_commit = asyncio.run(get_commitment(db, imported["id"]))
    assert imp_commit["commitment_yaml"] == orig_commit["commitment_yaml"]


def test_import_name_conflict(db, agent_with_skill, user, tmp_path):
    """Import same config twice for same user should raise ValueError."""
    from src.crud.export import export_agent
    from src.crud.import_agent import import_agent

    agent, _, _ = agent_with_skill
    export_dir = tmp_path / "exported"

    asyncio.run(export_agent(db, agent["id"], export_dir))

    # First import for u2 should succeed
    asyncio.run(import_agent(db, "u2", export_dir))

    # Second import for u2 should fail with name conflict
    with pytest.raises(ValueError, match="already exists"):
        asyncio.run(import_agent(db, "u2", export_dir))


def test_import_missing_scope(db, user, tmp_path):
    """Source dir missing agent/scope/scope.md should raise ValueError."""
    from src.crud.import_agent import import_agent

    # Create minimal source dir with pyproject.toml but no scope
    source_dir = tmp_path / "incomplete"
    source_dir.mkdir()
    (source_dir / "pyproject.toml").write_text(
        '[project]\nname = "broken-agent"\n', encoding="utf-8"
    )
    (source_dir / "agent" / "role").mkdir(parents=True)

    with pytest.raises(ValueError, match="Missing required file.*scope.md"):
        asyncio.run(import_agent(db, "u1", source_dir))
