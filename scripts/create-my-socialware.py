#!/usr/bin/env python3
"""create-my-socialware — Create a new Socialware App instance.

Similar to mix phx.new or npx create-next-app.
Copies the template to .socialware/workspace/{room}/{app}/.
Does NOT deploy — the developer does that after editing four primitives.

Usage:
    uv run scripts/create-my-socialware.py
    uv run scripts/create-my-socialware.py --room my-team --app task-manager
    uv run scripts/create-my-socialware.py --room my-team --app task-manager --description "Task management"
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent


def prompt_input(label: str, default: str = "") -> str:
    """Interactive input with default value support."""
    if default:
        raw = input(f"  {label} [{default}]: ").strip()
        return raw or default
    while True:
        raw = input(f"  {label}: ").strip()
        if raw:
            return raw
        print("    (cannot be empty)")


def create_workspace(room: str, app: str, description: str) -> Path:
    """Create workspace and copy templates."""
    workspace_dir = REPO_ROOT / ".socialware" / "workspace" / room / app
    if workspace_dir.exists():
        print(f"  Error: '{room}/{app}' already exists at {workspace_dir}")
        sys.exit(1)

    workspace_dir.mkdir(parents=True)

    # Copy src/
    src_src = REPO_ROOT / "src"
    src_dst = workspace_dir / "src"
    if src_src.exists():
        shutil.copytree(src_src, src_dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        print(f"  Copied src/")

    # Copy app/
    app_src = REPO_ROOT / "app"
    app_dst = workspace_dir / "app"
    if app_src.exists():
        shutil.copytree(app_src, app_dst, ignore=shutil.ignore_patterns("node_modules", ".next"))
        print(f"  Copied app/")

    # Copy agent/ (four primitives + deploy + start + adapters)
    agent_src = REPO_ROOT / "agent"
    agent_dst = workspace_dir / "agent"
    agent_dst.mkdir()

    for primitive in ["role", "scope", "commitment", "flow"]:
        prim_src = agent_src / primitive
        prim_dst = agent_dst / primitive
        if prim_src.exists():
            shutil.copytree(prim_src, prim_dst, ignore=shutil.ignore_patterns("__pycache__", "README.md"))
            print(f"  Copied agent/{primitive}/")

    # Copy deploy.sh, start.sh
    for script in ["deploy.sh", "start.sh"]:
        script_src = agent_src / script
        script_dst = agent_dst / script
        if script_src.exists():
            shutil.copy2(script_src, script_dst)
    print(f"  Copied agent/deploy.sh, agent/start.sh")

    # Copy adapters/
    adapters_src = agent_src / "adapters"
    adapters_dst = agent_dst / "adapters"
    if adapters_src.exists():
        shutil.copytree(adapters_src, adapters_dst, ignore=shutil.ignore_patterns("__pycache__"))
        print(f"  Copied agent/adapters/")

    return workspace_dir


def customize_workspace(workspace_dir: Path, app: str, description: str) -> None:
    """Customize the four primitives in the workspace."""

    # Rewrite scope/SOUL.md
    scope_soul = workspace_dir / "agent" / "scope" / "SOUL.md"
    scope_soul.write_text(f"""# {app}

{description}

## Capabilities

- Health check (/health)
- (Add your App capabilities here)

## Boundaries

- (Define the Agent's operational boundaries here)
""")
    print(f"  Customized agent/scope/SOUL.md")

    # Rewrite default role SOUL.md
    role_soul = workspace_dir / "agent" / "role" / "default" / "SOUL.md"
    if role_soul.exists():
        role_soul.write_text(f"""# Default Agent

You are the Agent for {app}.

## Identity

- Role: default
- Permissions: all operations

## Responsibilities

Operate {app} according to user instructions.
""")
        print(f"  Customized agent/role/default/SOUL.md")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new Socialware App instance")
    parser.add_argument("--room", help="Room name (workspace group)")
    parser.add_argument("--app", help="App name")
    parser.add_argument("--description", help="App description")
    args = parser.parse_args()

    print()
    print("create-my-socialware")
    print("=" * 40)
    print()

    room = args.room or prompt_input("Room name")
    app = args.app or prompt_input("App name")
    description = args.description or prompt_input("Description", f"{app} Socialware App")

    print()
    print(f"Creating {room}/{app}...")
    print()

    # 1. Create and copy
    workspace_dir = create_workspace(room, app, description)
    print()

    # 2. Customize
    customize_workspace(workspace_dir, app, description)

    ws_rel = f".socialware/workspace/{room}/{app}"
    print()
    print("=" * 40)
    print(f"Created '{room}/{app}' at {ws_rel}/")
    print()
    print("Next steps:")
    print(f"  cd {ws_rel}")
    print()
    print(f"  # Edit four primitives")
    print(f"  vim agent/scope/SOUL.md")
    print(f"  vim agent/role/default/SOUL.md")
    print(f"  vim agent/flow/")
    print()
    print(f"  # Deploy and start")
    print(f"  ./agent/deploy.sh")
    print(f"  ./agent/start.sh --role default")
    print()


if __name__ == "__main__":
    main()
