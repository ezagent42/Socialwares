"""Agent CRUD operations."""
from __future__ import annotations

import uuid
from src.db import Database


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


async def create_agent(db: Database, user_id: str, name: str, description: str, model: str = "claude") -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id FROM agents WHERE user_id = ? AND name = ?", (user_id, name)
        )
        if await cursor.fetchone():
            raise ValueError(f"Agent '{name}' already exists")

        agent_id = _uuid()
        await conn.execute(
            "INSERT INTO agents (id, user_id, name, description, model) VALUES (?, ?, ?, ?, ?)",
            (agent_id, user_id, name, description, model)
        )

        # Auto-create default role
        role_id = _uuid()
        default_soul = f"# Default Agent\n\nDefault role for {name}.\n\n## Identity\n\n- Role: default\n- Permissions: all operations\n"
        await conn.execute(
            "INSERT INTO roles (id, agent_id, name, soul_md) VALUES (?, ?, ?, ?)",
            (role_id, agent_id, "default", default_soul)
        )

        # Auto-create scope
        scope_id = _uuid()
        default_scope = f"# {name}\n\n{description}\n\n## Capabilities\n\n- (Add capabilities here)\n\n## Boundaries\n\n- (Add boundaries here)\n"
        await conn.execute(
            "INSERT INTO scopes (id, agent_id, soul_md) VALUES (?, ?, ?)",
            (scope_id, agent_id, default_scope)
        )

        # Auto-create empty commitment
        commit_id = _uuid()
        await conn.execute(
            "INSERT INTO commitments (id, agent_id, commitment_yaml) VALUES (?, ?, ?)",
            (commit_id, agent_id, "commitments: {}")
        )

        await conn.commit()
        return {
            "id": agent_id,
            "name": name,
            "description": description,
            "model": model,
            "roles": [{"id": role_id, "name": "default"}],
            "skills": [],
            "scope": {"id": scope_id},
        }
    finally:
        await conn.close()


async def list_agents(db: Database, user_id: str) -> list[dict]:
    conn = await db.connect()
    try:
        # Include user's agents + example agents (visible to all)
        cursor = await conn.execute(
            "SELECT id, name, description, model, is_example, created_at FROM agents WHERE user_id = ? OR is_example = 1 ORDER BY is_example DESC, created_at DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
        agents = []
        for row in rows:
            rc = await conn.execute("SELECT COUNT(*) FROM roles WHERE agent_id = ?", (row[0],))
            roles_count = (await rc.fetchone())[0]
            sc = await conn.execute("SELECT COUNT(*) FROM skills WHERE agent_id = ?", (row[0],))
            skills_count = (await sc.fetchone())[0]
            agents.append({
                "id": row[0], "name": row[1], "description": row[2], "model": row[3],
                "is_example": bool(row[4]),
                "roles_count": roles_count, "skills_count": skills_count,
            })
        return agents
    finally:
        await conn.close()


async def get_agent(db: Database, user_id: str, agent_id: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, name, description, model, is_example FROM agents WHERE id = ? AND (user_id = ? OR is_example = 1)",
            (agent_id, user_id)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Agent not found: {agent_id}")

        rc = await conn.execute("SELECT id, name, soul_md FROM roles WHERE agent_id = ?", (agent_id,))
        roles = [{"id": r[0], "name": r[1], "soul_md_preview": r[2][:100]} for r in await rc.fetchall()]

        sc = await conn.execute("SELECT id, name, description FROM skills WHERE agent_id = ?", (agent_id,))
        skills = [{"id": s[0], "name": s[1], "description": s[2]} for s in await sc.fetchall()]

        spc = await conn.execute("SELECT soul_md FROM scopes WHERE agent_id = ?", (agent_id,))
        scope_row = await spc.fetchone()

        cc = await conn.execute("SELECT commitment_yaml FROM commitments WHERE agent_id = ?", (agent_id,))
        commit_row = await cc.fetchone()

        return {
            "id": row[0], "name": row[1], "description": row[2], "model": row[3],
            "is_example": bool(row[4]),
            "roles": roles, "skills": skills,
            "scope": scope_row[0] if scope_row else "",
            "commitment": commit_row[0] if commit_row else "",
        }
    finally:
        await conn.close()


async def delete_agent(db: Database, user_id: str, agent_id: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT name FROM agents WHERE id = ? AND user_id = ?", (agent_id, user_id)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Agent not found: {agent_id}")
        name = row[0]
        await conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        await conn.commit()
        return {"id": agent_id, "name": name}
    finally:
        await conn.close()
