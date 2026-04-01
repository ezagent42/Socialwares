"""Export agent configuration from DB to complete runnable workspace."""
from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from src.db import Database
from src.crud.role_crud import list_roles
from src.crud.skill_crud import list_skills
from src.crud.scope_crud import get_scope
from src.crud.commitment_crud import get_commitment

# Template root — Socialwares repo root (contains agent/deploy.sh, agent/adapters/, etc.)
_TEMPLATE_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
# = .socialware/workspace/my-team/agentforge/src/crud/ → 6 levels up → Socialwares repo root


async def export_agent(db: Database, agent_id: str, output_dir: Path) -> dict:
    """Read agent config from DB, write to agent config package.

    output_dir/
    ├── Makefile
    ├── pyproject.toml
    └── agent/
        ├── role/{name}.md
        ├── scope/scope.md
        ├── commitment/commitment.yaml
        ├── flow/flow.yaml + {skill}/SKILL.md
        ├── adapters/         ← from template
        ├── deploy.sh         ← from template
        └── start.sh          ← from template

    No src/ or app/ — this is a pure Agent config package, not a full App.

    Returns: { agent_name, output_dir, files_generated, files }
    """
    # Fetch agent record
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, name, description FROM agents WHERE id = ?", (agent_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Agent not found: {agent_id}")
        agent_name = row[1]
        agent_desc = row[2] or ""
    finally:
        await conn.close()

    # Fetch all primitives
    roles = await list_roles(db, agent_id)
    skills = await list_skills(db, agent_id)
    scope = await get_scope(db, agent_id)
    commitment = await get_commitment(db, agent_id)

    output_dir = Path(output_dir)
    files: list[str] = []

    # ===== Four primitives (from DB) =====

    # -- Roles --
    role_dir = output_dir / "agent" / "role"
    role_dir.mkdir(parents=True, exist_ok=True)
    for role in roles:
        safe_name = _safe_filename(role["name"])
        role_file = role_dir / f"{safe_name}.md"
        role_file.write_text(role["soul_md"], encoding="utf-8")
        files.append(f"agent/role/{safe_name}.md")

    # -- Scope --
    scope_dir = output_dir / "agent" / "scope"
    scope_dir.mkdir(parents=True, exist_ok=True)
    scope_file = scope_dir / "scope.md"
    scope_file.write_text(scope["soul_md"], encoding="utf-8")
    files.append("agent/scope/scope.md")

    # -- Commitment --
    commitment_dir = output_dir / "agent" / "commitment"
    commitment_dir.mkdir(parents=True, exist_ok=True)
    commitment_file = commitment_dir / "commitment.yaml"
    commitment_file.write_text(commitment["commitment_yaml"], encoding="utf-8")
    files.append("agent/commitment/commitment.yaml")

    # -- Skills + flow.yaml --
    flow_dir = output_dir / "agent" / "flow"
    flow_dir.mkdir(parents=True, exist_ok=True)

    direct_actions = []
    for skill in skills:
        safe_name = _safe_filename(skill["name"])
        skill_dir = flow_dir / safe_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(skill["skill_md"], encoding="utf-8")
        files.append(f"agent/flow/{safe_name}/SKILL.md")

        role_names = [r["name"] for r in skill["roles"]]
        direct_actions.append({
            "action": skill["name"],
            "role": role_names,
            "description": skill.get("description", ""),
        })

    flow_data = {"flows": {}, "direct_actions": direct_actions}
    flow_file = flow_dir / "flow.yaml"
    flow_file.write_text(
        yaml.dump(flow_data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    files.append("agent/flow/flow.yaml")

    # ===== Runtime tools (from template) =====

    template_agent = _TEMPLATE_ROOT / "agent"

    # deploy.sh
    _copy_if_exists(template_agent / "deploy.sh", output_dir / "agent" / "deploy.sh", files)

    # start.sh
    _copy_if_exists(template_agent / "start.sh", output_dir / "agent" / "start.sh", files)

    # adapters/
    adapters_src = template_agent / "adapters"
    if adapters_src.exists():
        adapters_dst = output_dir / "agent" / "adapters"
        shutil.copytree(adapters_src, adapters_dst, dirs_exist_ok=True)
        for f in adapters_dst.rglob("*"):
            if f.is_file():
                files.append(str(f.relative_to(output_dir)))

    # Makefile.template → Makefile
    makefile_template = template_agent / "Makefile.template"
    if makefile_template.exists():
        shutil.copy2(makefile_template, output_dir / "Makefile")
        files.append("Makefile")

    # pyproject.toml (minimal — only agent runtime deps)
    pyproject_content = (
        "[project]\n"
        f'name = "{agent_name}"\n'
        f'description = "{agent_desc}"\n'
        'version = "0.1.0"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = ["pyyaml>=6.0"]\n'
        "\n"
        "[project.optional-dependencies]\n"
        'claude = ["claude-agent-sdk>=0.1.16"]\n'
        'codex = ["openai-agents>=0.10.0"]\n'
    )
    pyproject_file = output_dir / "pyproject.toml"
    pyproject_file.write_text(pyproject_content, encoding="utf-8")
    files.append("pyproject.toml")

    return {
        "agent_name": agent_name,
        "output_dir": str(output_dir),
        "files_generated": len(files),
        "files": files,
    }


def _safe_filename(name: str) -> str:
    """Sanitize a string for use as a file/directory name."""
    import re
    # Keep only alphanumeric, dash, underscore, dot
    safe = re.sub(r'[^\w\-.]', '_', name.strip())
    # Collapse multiple underscores
    safe = re.sub(r'_+', '_', safe).strip('_')
    return safe or "unnamed"


def _copy_if_exists(src: Path, dst: Path, files: list[str]) -> None:
    """Copy file if source exists, track in files list."""
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        # Make shell scripts executable
        if dst.suffix == ".sh":
            dst.chmod(0o755)


async def export_agent_zip(db: Database, agent_id: str) -> tuple[Path, str]:
    """Export agent config as a zip file for browser download.

    Returns: (zip_path, agent_name)
    """
    import tempfile
    import zipfile

    tmp_dir = Path(tempfile.mkdtemp())
    result = await export_agent(db, agent_id, tmp_dir / "export")

    agent_name = result["agent_name"]
    zip_path = tmp_dir / f"{agent_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        export_root = tmp_dir / "export"
        for file_path in export_root.rglob("*"):
            if file_path.is_file():
                arcname = str(file_path.relative_to(export_root))
                zf.write(file_path, arcname)

    return zip_path, agent_name
