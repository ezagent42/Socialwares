"""Cursor format adapter."""
from __future__ import annotations
from pathlib import Path
from src.db import Database
from src.adapters.base_export import BaseExportAdapter


class CursorAdapter(BaseExportAdapter):
    @staticmethod
    async def export(db: Database, agent_id: str, output_dir: Path) -> dict:
        agent = await BaseExportAdapter._load_agent(db, agent_id)
        output_dir = Path(output_dir)
        files = []

        cursor_dir = output_dir / ".cursor"
        cursor_dir.mkdir(parents=True, exist_ok=True)

        # .cursor/rules — single merged file
        parts = [agent["role_md"] or f"# {agent['name']}"]
        for skill in agent["skills"]:
            parts.append(f"\n---\n\n## Skill: {skill['name']}\n\n{skill['skill_md'] or skill['description']}")
        (cursor_dir / "rules").write_text("\n".join(parts), encoding="utf-8")
        files.append(".cursor/rules")

        return {"agent_name": agent["name"], "format": "cursor", "output_dir": str(output_dir), "files_generated": len(files), "files": files}
