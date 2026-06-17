"""GitAgent standard format adapter."""
from __future__ import annotations
from pathlib import Path
import yaml
from src.db import Database
from src.adapters.base_export import BaseExportAdapter


class GitAgentAdapter(BaseExportAdapter):
    @staticmethod
    async def export(db: Database, agent_id: str, output_dir: Path) -> dict:
        agent = await BaseExportAdapter._load_agent(db, agent_id)
        output_dir = Path(output_dir)
        files = []

        # agent.yaml
        agent_yaml = {
            "name": agent["name"],
            "version": "1.0.0",
            "description": agent["description"],
            "skills": [s["name"] for s in agent["skills"]],
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "agent.yaml").write_text(yaml.dump(agent_yaml, default_flow_style=False, sort_keys=False), encoding="utf-8")
        files.append("agent.yaml")

        # SOUL.md
        (output_dir / "SOUL.md").write_text(agent["role_md"] or "", encoding="utf-8")
        files.append("SOUL.md")

        # skills/
        for skill in agent["skills"]:
            skill_dir = output_dir / "skills" / skill["name"]
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(skill["skill_md"] or "", encoding="utf-8")
            files.append(f"skills/{skill['name']}/SKILL.md")

        return {"agent_name": agent["name"], "format": "gitagent", "output_dir": str(output_dir), "files_generated": len(files), "files": files}
