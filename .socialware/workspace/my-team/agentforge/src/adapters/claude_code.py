"""Claude Code format adapter."""
from __future__ import annotations
from pathlib import Path
from src.db import Database
from src.adapters.base_export import BaseExportAdapter


class ClaudeCodeAdapter(BaseExportAdapter):
    @staticmethod
    async def export(db: Database, agent_id: str, output_dir: Path) -> dict:
        agent = await BaseExportAdapter._load_agent(db, agent_id)
        output_dir = Path(output_dir)
        files = []

        output_dir.mkdir(parents=True, exist_ok=True)

        # CLAUDE.md — merged identity + skills
        parts = [agent["role_md"] or f"# {agent['name']}"]
        if agent["skills"]:
            parts.append("\n## Available Skills\n")
            for s in agent["skills"]:
                parts.append(f"- **{s['name']}**: {s['description']}")
        (output_dir / "CLAUDE.md").write_text("\n".join(parts), encoding="utf-8")
        files.append("CLAUDE.md")

        # .claude/skills/
        for skill in agent["skills"]:
            skill_dir = output_dir / ".claude" / "skills" / skill["name"]
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(skill["skill_md"] or "", encoding="utf-8")
            files.append(f".claude/skills/{skill['name']}/SKILL.md")

        return {"agent_name": agent["name"], "format": "claude-code", "output_dir": str(output_dir), "files_generated": len(files), "files": files}
