# tests/test_scope_commitment_crud.py
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


@pytest.fixture
def agent(db, user_id):
    """Create a test agent and return the agent dict."""
    from src.crud.agent_crud import create_agent
    return asyncio.run(create_agent(db, user_id, "test-agent", "A test agent"))


def test_get_scope(db, agent):
    from src.crud.scope_crud import get_scope
    scope = asyncio.run(get_scope(db, agent["id"]))
    assert scope["agent_id"] == agent["id"]
    assert "id" in scope
    assert len(scope["soul_md"]) > 0


def test_update_scope(db, agent):
    from src.crud.scope_crud import get_scope, update_scope
    new_soul = "# Updated Scope\n\nNew scope content.\n"
    updated = asyncio.run(update_scope(db, agent["id"], new_soul))
    assert updated["soul_md"] == new_soul
    # Verify via get
    fetched = asyncio.run(get_scope(db, agent["id"]))
    assert fetched["soul_md"] == new_soul


def test_get_commitment(db, agent):
    from src.crud.commitment_crud import get_commitment
    commitment = asyncio.run(get_commitment(db, agent["id"]))
    assert commitment["agent_id"] == agent["id"]
    assert "id" in commitment
    assert commitment["commitment_yaml"] == "commitments: {}"


def test_update_commitment(db, agent):
    from src.crud.commitment_crud import get_commitment, update_commitment
    new_yaml = "commitments:\n  max_response_time: 5s\n  availability: 99.9%\n"
    updated = asyncio.run(update_commitment(db, agent["id"], new_yaml))
    assert updated["commitment_yaml"] == new_yaml
    # Verify via get
    fetched = asyncio.run(get_commitment(db, agent["id"]))
    assert fetched["commitment_yaml"] == new_yaml
