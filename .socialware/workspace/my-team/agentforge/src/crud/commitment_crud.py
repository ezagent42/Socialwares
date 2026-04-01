"""Commitment CRUD operations."""
from __future__ import annotations

from src.db import Database


async def get_commitment(db: Database, agent_id: str) -> dict:
    """Return the commitment for an agent: {id, agent_id, commitment_yaml}."""
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, agent_id, commitment_yaml FROM commitments WHERE agent_id = ?",
            (agent_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Commitment not found for agent: {agent_id}")
        return {"id": row[0], "agent_id": row[1], "commitment_yaml": row[2]}
    finally:
        await conn.close()


async def update_commitment(db: Database, agent_id: str, commitment_yaml: str) -> dict:
    """Update the commitment YAML for an agent and return the updated record."""
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "UPDATE commitments SET commitment_yaml = ?, updated_at = datetime('now') WHERE agent_id = ?",
            (commitment_yaml, agent_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Commitment not found for agent: {agent_id}")
        await conn.commit()
        return await get_commitment(db, agent_id)
    finally:
        await conn.close()
