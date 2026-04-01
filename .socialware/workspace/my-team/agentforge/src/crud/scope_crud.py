"""Scope CRUD operations."""
from __future__ import annotations

from src.db import Database


async def get_scope(db: Database, agent_id: str) -> dict:
    """Return the scope for an agent: {id, agent_id, soul_md}."""
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, agent_id, soul_md FROM scopes WHERE agent_id = ?",
            (agent_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Scope not found for agent: {agent_id}")
        return {"id": row[0], "agent_id": row[1], "soul_md": row[2]}
    finally:
        await conn.close()


async def update_scope(db: Database, agent_id: str, soul_md: str) -> dict:
    """Update the scope soul_md for an agent and return the updated record."""
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "UPDATE scopes SET soul_md = ?, updated_at = datetime('now') WHERE agent_id = ?",
            (soul_md, agent_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Scope not found for agent: {agent_id}")
        await conn.commit()
        return await get_scope(db, agent_id)
    finally:
        await conn.close()
