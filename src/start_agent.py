#!/usr/bin/env python3
"""Production mode agent launch entry point.

The app backend calls this script to launch agents via adapters in SDK mode.
Complementary to agent/start.sh (CLI mode shell launch), no conflict.

Works relative to its own location — workspace-local, same as deploy.sh/start.sh.
Looks for .runtime/ in the parent directory of src/.

Usage (from within a workspace):
    python src/start_agent.py --role default
    python src/start_agent.py --role admin,reviewer
    python src/start_agent.py --role admin --adapter codex
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path


def load_adapter(adapter_name: str, project_dir: Path):
    """Dynamically load the adapter for the specified platform."""
    # Adapter lives in agent/adapters/ relative to workspace root
    app_root = Path(__file__).parent.parent
    adapter_path = app_root / "agent" / "adapters"
    sys.path.insert(0, str(adapter_path))
    sys.path.insert(0, str(adapter_path / adapter_name))

    from base import RoleConfig

    config = RoleConfig.from_runtime(project_dir)

    # Dynamically import the adapter module
    mod = importlib.import_module(f"{adapter_name}.sdk")

    # Find subclass of BaseAdapter
    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if (
            isinstance(attr, type)
            and hasattr(attr, "launch_sdk")
            and attr_name != "BaseAdapter"
        ):
            return attr(config)

    raise RuntimeError(f"No adapter class found in {adapter_name}/sdk.py")


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch Socialware Agent (production mode)")
    parser.add_argument("--role", required=True, help="Role name(s), comma-separated")
    parser.add_argument("--adapter", default="claude", help="Platform adapter")
    args = parser.parse_args()

    # Workspace-local: .runtime/ is in parent of src/
    app_root = Path(__file__).parent.parent
    runtime_dir = app_root / ".runtime"

    if not runtime_dir.exists():
        print(f"Error: .runtime/ not found at {runtime_dir}")
        print("Run ./agent/deploy.sh first")
        sys.exit(1)

    roles = args.role.split(",")

    for role_name in roles:
        project_dir = runtime_dir / "agents" / role_name.strip()
        if not project_dir.exists():
            print(f"Error: Role '{role_name}' not found at {project_dir}")
            sys.exit(1)

        print(f"Launching {role_name} via {args.adapter} SDK...")
        adapter = load_adapter(args.adapter, project_dir)
        adapter.launch_sdk()


if __name__ == "__main__":
    main()
