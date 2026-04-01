"""Role CRUD operations."""
from __future__ import annotations

import uuid
from src.db import Database


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


async def create_role(db: Database, agent_id: str, name: str, soul_md: str) -> dict:
    import re
    name = re.sub(r'[^\w\-]', '_', name.strip()).strip('_')
    if not name:
        raise ValueError("Role name is required")
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id FROM roles WHERE agent_id = ? AND name = ?", (agent_id, name)
        )
        if await cursor.fetchone():
            raise ValueError(f"Role '{name}' already exists for this agent")

        role_id = _uuid()
        await conn.execute(
            "INSERT INTO roles (id, agent_id, name, soul_md) VALUES (?, ?, ?, ?)",
            (role_id, agent_id, name, soul_md),
        )
        await conn.commit()
        return {"id": role_id, "agent_id": agent_id, "name": name, "soul_md": soul_md}
    finally:
        await conn.close()


async def list_roles(db: Database, agent_id: str) -> list[dict]:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, agent_id, name, soul_md, created_at, updated_at "
            "FROM roles WHERE agent_id = ? ORDER BY created_at",
            (agent_id,),
        )
        rows = await cursor.fetchall()
        return [
            {"id": r[0], "agent_id": r[1], "name": r[2], "soul_md": r[3],
             "created_at": r[4], "updated_at": r[5]}
            for r in rows
        ]
    finally:
        await conn.close()


async def update_role(db: Database, role_id: str, soul_md: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, agent_id, name FROM roles WHERE id = ?", (role_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Role not found: {role_id}")

        await conn.execute(
            "UPDATE roles SET soul_md = ?, updated_at = datetime('now') WHERE id = ?",
            (soul_md, role_id),
        )
        await conn.commit()
        return {"id": row[0], "agent_id": row[1], "name": row[2], "soul_md": soul_md}
    finally:
        await conn.close()


async def delete_role(db: Database, role_id: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, agent_id, name FROM roles WHERE id = ?", (role_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Role not found: {role_id}")

        agent_id = row[1]
        count_cursor = await conn.execute(
            "SELECT COUNT(*) FROM roles WHERE agent_id = ?", (agent_id,)
        )
        count = (await count_cursor.fetchone())[0]
        if count <= 1:
            raise ValueError("at least one")

        await conn.execute("DELETE FROM roles WHERE id = ?", (role_id,))
        await conn.commit()
        return {"id": row[0], "agent_id": agent_id, "name": row[2]}
    finally:
        await conn.close()
