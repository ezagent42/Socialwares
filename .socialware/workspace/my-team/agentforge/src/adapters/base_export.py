"""Base export adapter interface."""
from __future__ import annotations
from pathlib import Path
from src.db import Database
from src.crud.agent_crud import get_agent


class BaseExportAdapter:
    @staticmethod
    async def _load_agent(db: Database, agent_id: str) -> dict:
        """Load agent data. Uses __system__ user to access example agents too."""
        conn = await db.connect()
        try:
            cursor = await conn.execute(
                "SELECT id, name, description, role_md, is_example FROM agents WHERE id = ?", (agent_id,)
            )
            row = await cursor.fetchone()
            if not row:
                raise ValueError(f"Agent not found: {agent_id}")
            sc = await conn.execute("SELECT id, name, description, skill_md FROM skills WHERE agent_id = ?", (agent_id,))
            skills = [{"id": s[0], "name": s[1], "description": s[2], "skill_md": s[3]} for s in await sc.fetchall()]
            return {"id": row[0], "name": row[1], "description": row[2], "role_md": row[3], "is_example": bool(row[4]), "skills": skills}
        finally:
            await conn.close()

    @staticmethod
    async def export(db: Database, agent_id: str, output_dir: Path) -> dict:
        raise NotImplementedError
