#!/usr/bin/env python3
"""Generate agent definitions from SW App role config.

Reads a SW App's config.yaml, extracts roles, generates GitAgent agent
definitions in agent/agents/ directory.

Usage:
  uv run generate_from_roles.py --config ../taskarena/config.yaml
  uv run generate_from_roles.py --config ../taskarena/config.yaml --adapter codex
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_shared"))
from config import load_skill_config

AGENTS_DIR = Path(__file__).parent.parent.parent.parent / "agents"


def generate_agent(
    domain: str,
    role_id: str,
    role_config: dict,
    adapter: str,
) -> dict:
    """Generate a GitAgent agent definition from a role config."""
    agent_name = f"{domain}-{role_config['name']}"
    agent_dir = AGENTS_DIR / agent_name

    agent_yaml = {
        "name": agent_name,
        "version": "0.1.0",
        "description": f"Auto-generated agent for {domain} role {role_id} ({role_config['label']})",
        "model": {"preferred": "claude-sonnet-4-6"},
        "tags": [domain, role_id, "auto-generated"],
    }

    soul_md = f"""# {role_config['label']} Agent

你是 {domain} 的 {role_config['label']}。

## 角色

- 角色 ID: {role_id}
- 权限: {', '.join(role_config.get('permissions', []))}

## 职责

根据 {domain} 的流程规则，执行 {role_id} 角色允许的操作。
"""

    return {
        "name": agent_name,
        "dir": str(agent_dir),
        "agent_yaml": agent_yaml,
        "soul_md": soul_md,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate agents from role config")
    parser.add_argument("--config", required=True, help="Path to SW App config.yaml")
    parser.add_argument("--adapter", default="claude", choices=["claude", "codex", "kimicode"])
    parser.add_argument("--dry-run", action="store_true", help="Print without creating files")
    args = parser.parse_args()

    config_path = Path(args.config)
    with open(config_path) as f:
        config = yaml.safe_load(f)

    domain = config.get("domain", config_path.parent.name)
    roles = config.get("roles", {})

    generated = []
    for role_id, role_config in roles.items():
        agent = generate_agent(domain, role_id, role_config, args.adapter)
        generated.append(agent)

        if not args.dry_run:
            agent_dir = Path(agent["dir"])
            agent_dir.mkdir(parents=True, exist_ok=True)
            with open(agent_dir / "agent.yaml", "w") as f:
                yaml.dump(agent["agent_yaml"], f, allow_unicode=True, default_flow_style=False)
            with open(agent_dir / "SOUL.md", "w") as f:
                f.write(agent["soul_md"])

    print(json.dumps(generated, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
