# tests/test_auth.py
import pytest
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock


@pytest.fixture
def db(tmp_path):
    from src.db import Database
    database = Database(tmp_path / "test.db")
    asyncio.run(database.init())
    return database


def test_get_current_user_no_cookie(db):
    """No session cookie -> 401."""
    from src.auth import get_current_user
    from fastapi import HTTPException
    request = MagicMock()
    request.cookies = {}
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(request, db))
    assert exc_info.value.status_code == 401


def test_get_current_user_valid_session(db):
    """Valid session -> returns user dict."""
    from src.auth import get_current_user
    # Setup: create user + session
    async def _setup():
        conn = await db.connect()
        await conn.execute(
            "INSERT INTO users (id, github_id, github_login, github_name, github_avatar) VALUES (?, ?, ?, ?, ?)",
            ("u1", 123, "testuser", "Test User", "https://avatar.url")
        )
        session_id = uuid.uuid4().hex
        expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        await conn.execute(
            "INSERT INTO sessions (id, user_id, expires_at) VALUES (?, ?, ?)",
            (session_id, "u1", expires)
        )
        await conn.commit()
        await conn.close()
        return session_id
    session_id = asyncio.run(_setup())

    request = MagicMock()
    request.cookies = {"session_id": session_id}
    user = asyncio.run(get_current_user(request, db))
    assert user["id"] == "u1"
    assert user["github_login"] == "testuser"


def test_get_current_user_expired_session(db):
    """Expired session -> 401."""
    from src.auth import get_current_user
    from fastapi import HTTPException
    async def _setup():
        conn = await db.connect()
        await conn.execute(
            "INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)",
            ("u1", 123, "testuser")
        )
        session_id = uuid.uuid4().hex
        expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        await conn.execute(
            "INSERT INTO sessions (id, user_id, expires_at) VALUES (?, ?, ?)",
            (session_id, "u1", expired)
        )
        await conn.commit()
        await conn.close()
        return session_id
    session_id = asyncio.run(_setup())

    request = MagicMock()
    request.cookies = {"session_id": session_id}
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(request, db))
    assert exc_info.value.status_code == 401


def test_logout_clears_session(db):
    """Logout removes session from DB."""
    from src.auth import logout
    async def _setup():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('u1', 1, 'test')")
        await conn.execute("INSERT INTO sessions (id, user_id, expires_at) VALUES ('sess1', 'u1', '2099-01-01')")
        await conn.commit()
        await conn.close()
    asyncio.run(_setup())

    request = MagicMock()
    request.cookies = {"session_id": "sess1"}
    response = asyncio.run(logout(request, db))
    assert response.status_code == 200

    # Verify session deleted
    async def _check():
        conn = await db.connect()
        cursor = await conn.execute("SELECT COUNT(*) FROM sessions WHERE id = 'sess1'")
        count = (await cursor.fetchone())[0]
        await conn.close()
        return count
    assert asyncio.run(_check()) == 0
