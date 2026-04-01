"""Import agent configuration from standard four-primitive file structure into DB."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import yaml

from src.db import Database


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


def _parse_agent_name(source_dir: Path) -> str:
    """Parse agent name from pyproject.toml [project] section."""
    toml_path = source_dir / "pyproject.toml"
    if not toml_path.exists():
        raise ValueError(f"Missing pyproject.toml in {source_dir}")
    text = toml_path.read_text(encoding="utf-8")
    match = re.search(r'^name\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise ValueError("Could not parse agent name from pyproject.toml")
    return match.group(1)


async def import_agent(db: Database, user_id: str, source_dir: Path) -> dict:
    """Parse standard four-primitive file structure and import into DB.

    Reads:
    - agent/role/*.md -> roles table
    - agent/scope/scope.md -> scopes table
    - agent/flow/*/SKILL.md -> skills table
    - agent/flow/flow.yaml -> skill_roles mapping
    - agent/commitment/commitment.yaml -> commitments table
    - pyproject.toml -> agent name/description

    Returns: same format as create_agent (id, name, description, roles, skills)
    """
    source_dir = Path(source_dir)

    # 1. Read agent name from pyproject.toml
    agent_name = _parse_agent_name(source_dir)

    # 2. Validate scope exists
    scope_path = source_dir / "agent" / "scope" / "scope.md"
    if not scope_path.exists():
        raise ValueError(
            f"Missing required file: agent/scope/scope.md in {source_dir}"
        )

    # 3. Check name conflict
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id FROM agents WHERE user_id = ? AND name = ?",
            (user_id, agent_name),
        )
        if await cursor.fetchone():
            raise ValueError(f"Agent '{agent_name}' already exists")

        # 4. Insert agent record
        agent_id = _uuid()
        await conn.execute(
            "INSERT INTO agents (id, user_id, name, description) VALUES (?, ?, ?, ?)",
            (agent_id, user_id, agent_name, ""),
        )

        # 5. Read and insert roles
        role_dir = source_dir / "agent" / "role"
        role_map: dict[str, str] = {}  # role_name -> role_id
        roles_result: list[dict] = []
        if role_dir.is_dir():
            for role_file in sorted(role_dir.glob("*.md")):
                role_name = role_file.stem
                soul_md = role_file.read_text(encoding="utf-8")
                role_id = _uuid()
                await conn.execute(
                    "INSERT INTO roles (id, agent_id, name, soul_md) VALUES (?, ?, ?, ?)",
                    (role_id, agent_id, role_name, soul_md),
                )
                role_map[role_name] = role_id
                roles_result.append({"id": role_id, "name": role_name})

        # 6. Insert scope
        scope_id = _uuid()
        scope_md = scope_path.read_text(encoding="utf-8")
        await conn.execute(
            "INSERT INTO scopes (id, agent_id, soul_md) VALUES (?, ?, ?)",
            (scope_id, agent_id, scope_md),
        )

        # 7. Insert commitment
        commitment_path = source_dir / "agent" / "commitment" / "commitment.yaml"
        commit_id = _uuid()
        commitment_yaml = (
            commitment_path.read_text(encoding="utf-8")
            if commitment_path.exists()
            else "commitments: {}"
        )
        await conn.execute(
            "INSERT INTO commitments (id, agent_id, commitment_yaml) VALUES (?, ?, ?)",
            (commit_id, agent_id, commitment_yaml),
        )

        # 8. Parse flow.yaml for action->role mapping
        flow_path = source_dir / "agent" / "flow" / "flow.yaml"
        action_role_map: dict[str, list[str]] = {}  # action_name -> [role_names]
        action_desc_map: dict[str, str] = {}  # action_name -> description
        if flow_path.exists():
            flow_data = yaml.safe_load(
                flow_path.read_text(encoding="utf-8")
            )
            for action in flow_data.get("direct_actions", []):
                action_name = action["action"]
                action_role_map[action_name] = action.get("role", [])
                action_desc_map[action_name] = action.get("description", "")

        # 9. Read and insert skills
        flow_dir = source_dir / "agent" / "flow"
        skills_result: list[dict] = []
        if flow_dir.is_dir():
            for skill_dir in sorted(flow_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / "SKILL.md"
                if not skill_file.exists():
                    continue
                skill_name = skill_dir.name
                skill_md = skill_file.read_text(encoding="utf-8")
                description = action_desc_map.get(skill_name, "")

                skill_id = _uuid()
                await conn.execute(
                    "INSERT INTO skills (id, agent_id, name, description, skill_md) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (skill_id, agent_id, skill_name, description, skill_md),
                )

                # Create skill_roles based on flow.yaml mapping
                mapped_role_names = action_role_map.get(skill_name, [])
                for rname in mapped_role_names:
                    rid = role_map.get(rname)
                    if rid:
                        await conn.execute(
                            "INSERT INTO skill_roles (skill_id, role_id) VALUES (?, ?)",
                            (skill_id, rid),
                        )

                skills_result.append({"id": skill_id, "name": skill_name})

        await conn.commit()

        return {
            "id": agent_id,
            "name": agent_name,
            "description": "",
            "roles": roles_result,
            "skills": skills_result,
            "scope": {"id": scope_id},
        }
    finally:
        await conn.close()
