"""Skill CRUD operations."""
from __future__ import annotations

import uuid
from src.db import Database


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


async def create_skill(
    db: Database, agent_id: str, name: str, skill_md: str,
    role_ids: list[str], description: str = "",
) -> dict:
    if not role_ids:
        raise ValueError("At least one role_id is required")
    # Sanitize name — only allow alphanumeric, dash, underscore
    import re
    name = re.sub(r'[^\w\-]', '_', name.strip()).strip('_')
    if not name:
        raise ValueError("Skill name is required")

    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id FROM skills WHERE agent_id = ? AND name = ?",
            (agent_id, name),
        )
        if await cursor.fetchone():
            raise ValueError(f"Skill '{name}' already exists for this agent")

        skill_id = _uuid()
        await conn.execute(
            "INSERT INTO skills (id, agent_id, name, description, skill_md) VALUES (?, ?, ?, ?, ?)",
            (skill_id, agent_id, name, description, skill_md),
        )

        for rid in role_ids:
            await conn.execute(
                "INSERT INTO skill_roles (skill_id, role_id) VALUES (?, ?)",
                (skill_id, rid),
            )

        await conn.commit()

        # Fetch role names for the response
        placeholders = ",".join("?" for _ in role_ids)
        rc = await conn.execute(
            f"SELECT id, name FROM roles WHERE id IN ({placeholders})", role_ids,
        )
        roles = [{"id": r[0], "name": r[1]} for r in await rc.fetchall()]

        return {
            "id": skill_id,
            "agent_id": agent_id,
            "name": name,
            "description": description,
            "skill_md": skill_md,
            "roles": roles,
        }
    finally:
        await conn.close()


async def list_skills(db: Database, agent_id: str) -> list[dict]:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, name, description, skill_md FROM skills WHERE agent_id = ? ORDER BY created_at",
            (agent_id,),
        )
        rows = await cursor.fetchall()
        skills = []
        for row in rows:
            skill_id = row[0]
            rc = await conn.execute(
                "SELECT r.id, r.name FROM roles r "
                "JOIN skill_roles sr ON sr.role_id = r.id "
                "WHERE sr.skill_id = ?",
                (skill_id,),
            )
            roles = [{"id": r[0], "name": r[1]} for r in await rc.fetchall()]
            skills.append({
                "id": skill_id,
                "name": row[1],
                "description": row[2],
                "skill_md": row[3],
                "roles": roles,
            })
        return skills
    finally:
        await conn.close()


async def update_skill(
    db: Database, skill_id: str, skill_md: str | None = None,
    role_ids: list[str] | None = None,
) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, agent_id, name, description, skill_md FROM skills WHERE id = ?",
            (skill_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Skill not found: {skill_id}")

        if skill_md is not None:
            await conn.execute(
                "UPDATE skills SET skill_md = ?, updated_at = datetime('now') WHERE id = ?",
                (skill_md, skill_id),
            )

        if role_ids is not None:
            await conn.execute("DELETE FROM skill_roles WHERE skill_id = ?", (skill_id,))
            for rid in role_ids:
                await conn.execute(
                    "INSERT INTO skill_roles (skill_id, role_id) VALUES (?, ?)",
                    (skill_id, rid),
                )

        await conn.commit()

        # Re-fetch for response
        cursor = await conn.execute(
            "SELECT id, agent_id, name, description, skill_md FROM skills WHERE id = ?",
            (skill_id,),
        )
        row = await cursor.fetchone()
        rc = await conn.execute(
            "SELECT r.id, r.name FROM roles r "
            "JOIN skill_roles sr ON sr.role_id = r.id "
            "WHERE sr.skill_id = ?",
            (skill_id,),
        )
        roles = [{"id": r[0], "name": r[1]} for r in await rc.fetchall()]

        return {
            "id": row[0],
            "agent_id": row[1],
            "name": row[2],
            "description": row[3],
            "skill_md": row[4],
            "roles": roles,
        }
    finally:
        await conn.close()


async def delete_skill(db: Database, skill_id: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, name FROM skills WHERE id = ?", (skill_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Skill not found: {skill_id}")

        await conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
        await conn.commit()
        return {"id": row[0], "name": row[1]}
    finally:
        await conn.close()
