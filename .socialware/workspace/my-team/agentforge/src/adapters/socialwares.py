"""Socialwares four-primitives format adapter."""
from __future__ import annotations
import shutil
from pathlib import Path
import yaml
from src.db import Database
from src.adapters.base_export import BaseExportAdapter

_TEMPLATE_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent  # Socialwares repo root


class SocialwaresAdapter(BaseExportAdapter):
    @staticmethod
    async def export(db: Database, agent_id: str, output_dir: Path) -> dict:
        agent = await BaseExportAdapter._load_agent(db, agent_id)
        output_dir = Path(output_dir)
        files = []

        # role/default.md
        role_dir = output_dir / "agent" / "role"
        role_dir.mkdir(parents=True, exist_ok=True)
        (role_dir / "default.md").write_text(agent["role_md"] or "", encoding="utf-8")
        files.append("agent/role/default.md")

        # scope/scope.md (auto-generated)
        scope_dir = output_dir / "agent" / "scope"
        scope_dir.mkdir(parents=True, exist_ok=True)
        scope_md = f"# {agent['name']}\n\n{agent['description']}\n\n## Capabilities\n\n- (Add capabilities)\n\n## Boundaries\n\n- (Add boundaries)\n"
        (scope_dir / "scope.md").write_text(scope_md, encoding="utf-8")
        files.append("agent/scope/scope.md")

        # commitment/commitment.yaml (auto-generated empty)
        commit_dir = output_dir / "agent" / "commitment"
        commit_dir.mkdir(parents=True, exist_ok=True)
        (commit_dir / "commitment.yaml").write_text("commitments: {}\n", encoding="utf-8")
        files.append("agent/commitment/commitment.yaml")

        # flow/*/SKILL.md + flow.yaml
        flow_dir = output_dir / "agent" / "flow"
        flow_dir.mkdir(parents=True, exist_ok=True)
        direct_actions = []
        for skill in agent["skills"]:
            sd = flow_dir / skill["name"]
            sd.mkdir(parents=True, exist_ok=True)
            (sd / "SKILL.md").write_text(skill["skill_md"] or "", encoding="utf-8")
            files.append(f"agent/flow/{skill['name']}/SKILL.md")
            direct_actions.append({"action": skill["name"], "role": ["default"], "description": skill["description"]})
        flow_data = {"flows": {}, "direct_actions": direct_actions}
        (flow_dir / "flow.yaml").write_text(yaml.dump(flow_data, default_flow_style=False, sort_keys=False), encoding="utf-8")
        files.append("agent/flow/flow.yaml")

        # Template files
        template_agent = _TEMPLATE_ROOT / "agent"
        for f in ["deploy.sh", "start.sh"]:
            src = template_agent / f
            if src.exists():
                dst = output_dir / "agent" / f
                shutil.copy2(src, dst)
                if dst.suffix == ".sh":
                    dst.chmod(0o755)
                files.append(f"agent/{f}")
        adapters_src = template_agent / "adapters"
        if adapters_src.exists():
            shutil.copytree(adapters_src, output_dir / "agent" / "adapters", dirs_exist_ok=True)

        # Makefile
        makefile_src = template_agent / "Makefile.template"
        if makefile_src.exists():
            shutil.copy2(makefile_src, output_dir / "Makefile")
            files.append("Makefile")

        # pyproject.toml
        (output_dir / "pyproject.toml").write_text(
            f'[project]\nname = "{agent["name"]}"\nversion = "0.1.0"\nrequires-python = ">=3.12"\ndependencies = ["pyyaml>=6.0"]\n',
            encoding="utf-8"
        )
        files.append("pyproject.toml")

        return {"agent_name": agent["name"], "format": "socialwares", "output_dir": str(output_dir), "files_generated": len(files), "files": files}
