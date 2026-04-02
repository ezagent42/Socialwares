"""Agent CRUD — simplified model (name + role_md + skills, no model)."""
from __future__ import annotations
import re
import uuid
from src.db import Database


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


def _safe_name(name: str) -> str:
    name = re.sub(r'[^\w\-]', '_', name.strip()).strip('_')
    return name or "unnamed"


async def create_agent(db: Database, user_id: str, name: str, description: str, role_md: str) -> dict:
    name = _safe_name(name)
    conn = await db.connect()
    try:
        cursor = await conn.execute("SELECT id FROM agents WHERE user_id = ? AND name = ?", (user_id, name))
        if await cursor.fetchone():
            raise ValueError(f"Agent '{name}' already exists")
        agent_id = _uuid()
        await conn.execute(
            "INSERT INTO agents (id, user_id, name, description, role_md) VALUES (?, ?, ?, ?, ?)",
            (agent_id, user_id, name, description, role_md)
        )
        await conn.commit()
        return {"id": agent_id, "name": name, "description": description, "role_md": role_md, "skills": []}
    finally:
        await conn.close()


async def list_agents(db: Database, user_id: str) -> list[dict]:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, name, description, role_md, is_example FROM agents WHERE user_id = ? OR is_example = 1 ORDER BY is_example DESC, created_at DESC",
            (user_id,)
        )
        agents = []
        for row in await cursor.fetchall():
            sc = await conn.execute("SELECT COUNT(*) FROM skills WHERE agent_id = ?", (row[0],))
            skills_count = (await sc.fetchone())[0]
            agents.append({
                "id": row[0], "name": row[1], "description": row[2],
                "role_md_preview": (row[3] or "")[:100],
                "is_example": bool(row[4]), "skills_count": skills_count,
            })
        return agents
    finally:
        await conn.close()


async def get_agent(db: Database, user_id: str, agent_id: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, name, description, role_md, is_example FROM agents WHERE id = ? AND (user_id = ? OR is_example = 1)",
            (agent_id, user_id)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Agent not found: {agent_id}")
        sc = await conn.execute("SELECT id, name, description, skill_md FROM skills WHERE agent_id = ?", (agent_id,))
        skills = [{"id": s[0], "name": s[1], "description": s[2], "skill_md": s[3]} for s in await sc.fetchall()]
        return {
            "id": row[0], "name": row[1], "description": row[2],
            "role_md": row[3], "is_example": bool(row[4]), "skills": skills,
        }
    finally:
        await conn.close()


async def update_agent(db: Database, user_id: str, agent_id: str, role_md: str = None, description: str = None) -> dict:
    conn = await db.connect()
    try:
        if role_md is not None:
            await conn.execute("UPDATE agents SET role_md = ?, updated_at = datetime('now') WHERE id = ? AND user_id = ?", (role_md, agent_id, user_id))
        if description is not None:
            await conn.execute("UPDATE agents SET description = ?, updated_at = datetime('now') WHERE id = ? AND user_id = ?", (description, agent_id, user_id))
        await conn.commit()
        return await get_agent(db, user_id, agent_id)
    finally:
        await conn.close()


async def delete_agent(db: Database, user_id: str, agent_id: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute("SELECT name FROM agents WHERE id = ? AND user_id = ?", (agent_id, user_id))
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Agent not found: {agent_id}")
        name = row[0]
        await conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        await conn.commit()
        return {"id": agent_id, "name": name}
    finally:
        await conn.close()
