# tests/test_export.py
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


@pytest.fixture
def agent_with_skill(db, agent):
    """Add a custom role and a skill to the agent, return (agent, role, skill)."""
    async def _setup():
        from src.crud.role_crud import create_role
        from src.crud.skill_crud import create_skill

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


def test_export_creates_files(db, agent_with_skill, tmp_path):
    from src.crud.export import export_agent

    agent, role, skill = agent_with_skill
    output_dir = tmp_path / "output"

    result = asyncio.run(export_agent(db, agent["id"], output_dir))

    # Verify result structure
    assert result["agent_name"] == "test-agent"
    assert result["files_generated"] > 0
    assert len(result["files"]) == result["files_generated"]

    # Verify role files exist (default + greeter)
    assert (output_dir / "agent" / "role" / "default.md").exists()
    assert (output_dir / "agent" / "role" / "greeter.md").exists()

    # Verify scope
    assert (output_dir / "agent" / "scope" / "scope.md").exists()

    # Verify commitment
    assert (output_dir / "agent" / "commitment" / "commitment.yaml").exists()

    # Verify flow.yaml
    assert (output_dir / "agent" / "flow" / "flow.yaml").exists()

    # Verify skill directory
    assert (output_dir / "agent" / "flow" / "greet" / "SKILL.md").exists()

    # Verify pyproject.toml
    assert (output_dir / "pyproject.toml").exists()
    toml_text = (output_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "test-agent"' in toml_text
    assert 'requires-python = ">=3.12"' in toml_text


def test_export_flow_yaml_content(db, agent_with_skill, tmp_path):
    from src.crud.export import export_agent

    agent, role, skill = agent_with_skill
    output_dir = tmp_path / "output"

    asyncio.run(export_agent(db, agent["id"], output_dir))

    flow_yaml = yaml.safe_load(
        (output_dir / "agent" / "flow" / "flow.yaml").read_text(encoding="utf-8")
    )

    assert flow_yaml["flows"] == {}
    assert len(flow_yaml["direct_actions"]) == 1

    action = flow_yaml["direct_actions"][0]
    assert action["action"] == "greet"
    assert action["description"] == "Greeting skill"
    # Should have both roles mapped
    assert set(action["role"]) == {"default", "greeter"}


def test_export_role_content(db, agent_with_skill, tmp_path):
    from src.crud.export import export_agent

    agent, role, skill = agent_with_skill
    output_dir = tmp_path / "output"

    asyncio.run(export_agent(db, agent["id"], output_dir))

    # The greeter role file should contain the soul_md from DB
    greeter_md = (output_dir / "agent" / "role" / "greeter.md").read_text(
        encoding="utf-8"
    )
    assert greeter_md == "# Greeter Role\n\nYou greet people warmly.\n"

    # The default role should contain auto-generated content from create_agent
    default_md = (output_dir / "agent" / "role" / "default.md").read_text(
        encoding="utf-8"
    )
    assert "# Default Agent" in default_md
    assert "default" in default_md.lower()
