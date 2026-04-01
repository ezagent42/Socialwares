"""GitHub OAuth authentication."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import Request, Response, HTTPException
from fastapi.responses import RedirectResponse

from src.db import Database

log = logging.getLogger(__name__)

SESSION_EXPIRY_DAYS = 7
GITHUB_TIMEOUT = 15  # seconds


def _github_client_id() -> str:
    return os.getenv("GITHUB_CLIENT_ID", "")


def _github_client_secret() -> str:
    return os.getenv("GITHUB_CLIENT_SECRET", "")


def _frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:3000")


async def github_login(request: Request) -> RedirectResponse:
    """Redirect to GitHub OAuth authorization page."""
    client_id = _github_client_id()
    if not client_id:
        raise HTTPException(500, "GITHUB_CLIENT_ID not configured")
    redirect_uri = f"{_frontend_url()}/api/auth/callback"
    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=read:user"
    )
    return RedirectResponse(github_url)


async def github_callback(code: str, db: Database) -> Response:
    """Handle GitHub OAuth callback."""
    frontend_url = _frontend_url()

    # Exchange code for access token
    try:
        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": _github_client_id(),
                    "client_secret": _github_client_secret(),
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            token_data = token_resp.json()
    except httpx.TimeoutException:
        log.warning("GitHub token exchange timed out")
        return RedirectResponse(f"{frontend_url}?error=timeout", status_code=302)
    except Exception as e:
        log.error(f"GitHub token exchange failed: {e}")
        return RedirectResponse(f"{frontend_url}?error=network", status_code=302)

    # Check for GitHub error (e.g. expired/reused code)
    if "error" in token_data:
        error = token_data.get("error", "unknown")
        error_desc = token_data.get("error_description", "")
        log.warning(f"GitHub OAuth error: {error} — {error_desc}")
        return RedirectResponse(f"{frontend_url}?error={error}", status_code=302)

    access_token = token_data.get("access_token")
    if not access_token:
        log.warning(f"No access_token in response: {token_data}")
        return RedirectResponse(f"{frontend_url}?error=no_token", status_code=302)

    # Get user info
    try:
        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
            user_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_resp.status_code != 200:
                log.warning(f"GitHub user API returned {user_resp.status_code}")
                return RedirectResponse(f"{frontend_url}?error=user_fetch", status_code=302)
            user_data = user_resp.json()
    except httpx.TimeoutException:
        log.warning("GitHub user API timed out")
        return RedirectResponse(f"{frontend_url}?error=timeout", status_code=302)
    except Exception as e:
        log.error(f"GitHub user API failed: {e}")
        return RedirectResponse(f"{frontend_url}?error=network", status_code=302)

    github_id = user_data.get("id")
    github_login_name = user_data.get("login", "")
    github_name = user_data.get("name", "")
    github_avatar = user_data.get("avatar_url", "")

    if not github_id:
        log.warning(f"No github_id in user data: {user_data}")
        return RedirectResponse(f"{frontend_url}?error=invalid_user", status_code=302)

    # Create or update user + session
    conn = await db.connect()
    try:
        cursor = await conn.execute("SELECT id FROM users WHERE github_id = ?", (github_id,))
        row = await cursor.fetchone()
        if row:
            user_id = row[0]
            await conn.execute(
                "UPDATE users SET github_login=?, github_name=?, github_avatar=?, updated_at=datetime('now') WHERE id=?",
                (github_login_name, github_name, github_avatar, user_id)
            )
        else:
            user_id = uuid.uuid4().hex[:12]
            await conn.execute(
                "INSERT INTO users (id, github_id, github_login, github_name, github_avatar) VALUES (?, ?, ?, ?, ?)",
                (user_id, github_id, github_login_name, github_name, github_avatar)
            )

        session_id = uuid.uuid4().hex
        expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()
        await conn.execute(
            "INSERT INTO sessions (id, user_id, expires_at) VALUES (?, ?, ?)",
            (session_id, user_id, expires_at)
        )
        await conn.commit()
    except Exception as e:
        log.error(f"Database error during login: {e}")
        return RedirectResponse(f"{frontend_url}?error=db", status_code=302)
    finally:
        await conn.close()

    response = RedirectResponse(frontend_url, status_code=302)
    response.set_cookie(
        "session_id", session_id,
        httponly=True, max_age=SESSION_EXPIRY_DAYS * 86400, samesite="lax"
    )
    return response


async def get_current_user(request: Request, db: Database) -> dict:
    """Get current user from session cookie. Raises 401 if not logged in."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(401, "Not authenticated")

    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT u.id, u.github_login, u.github_name, u.github_avatar, s.expires_at "
            "FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(401, "Invalid session")

        # Check expiry
        expires_at = datetime.fromisoformat(row[4])
        if expires_at < datetime.now(timezone.utc):
            await conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await conn.commit()
            raise HTTPException(401, "Session expired")

        return {
            "id": row[0],
            "github_login": row[1],
            "github_name": row[2],
            "github_avatar": row[3],
        }
    finally:
        await conn.close()


async def logout(request: Request, db: Database) -> Response:
    """Clear session."""
    session_id = request.cookies.get("session_id")
    if session_id:
        conn = await db.connect()
        try:
            await conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await conn.commit()
        finally:
            await conn.close()

    response = Response(content='{"status": "logged out"}', media_type="application/json")
    response.delete_cookie("session_id")
    return response
