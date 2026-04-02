"""Skill CRUD — simplified (no role-based permissions)."""
from __future__ import annotations
import re
import uuid
from src.db import Database


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


async def create_skill(db: Database, agent_id: str, name: str, skill_md: str, description: str = "") -> dict:
    name = re.sub(r'[^\w\-]', '_', name.strip()).strip('_')
    if not name:
        raise ValueError("Skill name is required")
    conn = await db.connect()
    try:
        cursor = await conn.execute("SELECT id FROM skills WHERE agent_id = ? AND name = ?", (agent_id, name))
        if await cursor.fetchone():
            raise ValueError(f"Skill '{name}' already exists for this agent")
        skill_id = _uuid()
        await conn.execute(
            "INSERT INTO skills (id, agent_id, name, description, skill_md) VALUES (?, ?, ?, ?, ?)",
            (skill_id, agent_id, name, description, skill_md)
        )
        await conn.commit()
        return {"id": skill_id, "agent_id": agent_id, "name": name, "description": description, "skill_md": skill_md}
    finally:
        await conn.close()


async def list_skills(db: Database, agent_id: str) -> list[dict]:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, name, description, skill_md FROM skills WHERE agent_id = ? ORDER BY created_at", (agent_id,)
        )
        return [{"id": r[0], "name": r[1], "description": r[2], "skill_md": r[3]} for r in await cursor.fetchall()]
    finally:
        await conn.close()


async def update_skill(db: Database, skill_id: str, skill_md: str = None, description: str = None) -> dict:
    conn = await db.connect()
    try:
        if skill_md is not None:
            await conn.execute("UPDATE skills SET skill_md = ?, updated_at = datetime('now') WHERE id = ?", (skill_md, skill_id))
        if description is not None:
            await conn.execute("UPDATE skills SET description = ?, updated_at = datetime('now') WHERE id = ?", (description, skill_id))
        await conn.commit()
        cursor = await conn.execute("SELECT id, agent_id, name, description, skill_md FROM skills WHERE id = ?", (skill_id,))
        r = await cursor.fetchone()
        if not r:
            raise ValueError(f"Skill not found: {skill_id}")
        return {"id": r[0], "agent_id": r[1], "name": r[2], "description": r[3], "skill_md": r[4]}
    finally:
        await conn.close()


async def delete_skill(db: Database, skill_id: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute("SELECT id, name FROM skills WHERE id = ?", (skill_id,))
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Skill not found: {skill_id}")
        await conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
        await conn.commit()
        return {"id": row[0], "name": row[1]}
    finally:
        await conn.close()
