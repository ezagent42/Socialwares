import pytest
import subprocess
import json
import asyncio


@pytest.fixture
def db_path(tmp_path):
    from src.db import Database
    db = Database(tmp_path / "test.db")
    asyncio.run(db.init())
    # Seed a user
    async def _seed():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('u1', 1, 'test')")
        await conn.commit()
        await conn.close()
    asyncio.run(_seed())
    return str(tmp_path / "test.db")


def test_cli_create_agent(db_path):
    result = subprocess.run(
        ["uv", "run", "python", "-m", "src.crud.cli", "create-agent",
         "--db", db_path, "--user-id", "u1",
         "--name", "test-app", "--role-md", "# Test"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["name"] == "test-app"


def test_cli_list_agents(db_path):
    # Create first
    subprocess.run(
        ["uv", "run", "python", "-m", "src.crud.cli", "create-agent",
         "--db", db_path, "--user-id", "u1",
         "--name", "a1", "--role-md", "# A1"],
        capture_output=True, text=True, cwd="."
    )
    result = subprocess.run(
        ["uv", "run", "python", "-m", "src.crud.cli", "list-agents",
         "--db", db_path, "--user-id", "u1"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert len(data) >= 1
