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
    async def _setup():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('u1', 1, 'test')")
        await conn.execute("INSERT INTO agents (id, user_id, name, role_md) VALUES ('a1', 'u1', 'test-app', '# Test')")
        await conn.execute("INSERT INTO skills (id, agent_id, name, description, skill_md) VALUES ('s1', 'a1', 'review_code', 'Review code', '# Review Code\\nReview for bugs.')")
        await conn.commit()
        await conn.close()
        return "u1"
    return asyncio.run(_setup())


def test_search_finds_local_skill(db, user_id):
    from src.crud.find_skill import search_skills
    results = asyncio.run(search_skills(db, user_id, "review"))
    assert len(results) >= 1
    assert any(r["name"] == "review_code" and r["source"] == "local" for r in results)


def test_search_no_results(db, user_id):
    from src.crud.find_skill import search_skills
    results = asyncio.run(search_skills(db, user_id, "xyznonexistent"))
    local_results = [r for r in results if r["source"] == "local"]
    assert len(local_results) == 0


def test_search_returns_skill_md(db, user_id):
    from src.crud.find_skill import search_skills
    results = asyncio.run(search_skills(db, user_id, "review"))
    local = [r for r in results if r["source"] == "local"]
    assert len(local) >= 1
    assert "skill_md" in local[0]
    assert "Review Code" in local[0]["skill_md"]
