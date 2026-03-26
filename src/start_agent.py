#!/usr/bin/env python3
"""SDK mode agent launch — programmatic with full conversation logging.

Complementary to agent/start.sh (TUI mode). Use for:
- Production: app backend spawns agents via SDK
- Evolver: automated conversation testing

Usage (from within a workspace):
    uv run src/start_agent.py --role default --prompt "check health"
    uv run src/start_agent.py --role default --adapter codex --prompt "list tasks"
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import sys
from pathlib import Path


def load_adapter(adapter_name: str, project_dir: Path):
    """Dynamically load the adapter for the specified platform."""
    app_root = Path(__file__).parent.parent
    adapter_path = app_root / "agent" / "adapters"
    sys.path.insert(0, str(adapter_path))
    sys.path.insert(0, str(adapter_path / adapter_name))

    # Handle kimicode → kimicode directory
    actual_name = adapter_name
    if adapter_name == "kimi":
        actual_name = "kimicode"
        sys.path.insert(0, str(adapter_path / actual_name))

    from base import RoleConfig

    config = RoleConfig.from_runtime(project_dir)

    # Import adapter module
    mod = importlib.import_module(f"{actual_name}.sdk")

    # Find adapter class
    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if (
            isinstance(attr, type)
            and hasattr(attr, "launch_sdk")
            and attr_name != "BaseAdapter"
        ):
            return attr(config)

    raise RuntimeError(f"No adapter class found in {actual_name}/sdk.py")


async def run_sdk(adapter, prompt: str, workspace_root: Path, role: str, adapter_name: str) -> None:
    """Run SDK mode: send prompt, collect messages, save session."""
    from base import save_session, is_noise

    messages = []
    print(f"[SDK] Sending prompt to {role} via {adapter_name}...")
    print()

    try:
        async for message in adapter.launch_sdk(prompt):
            # SDK adapter yields pre-serialized dicts (via serialize())
            msg = message if isinstance(message, dict) else {"_type": "raw", "content": str(message)}

            # Skip system noise
            if is_noise(msg):
                continue

            messages.append(msg)

            # Print text content if present
            content = ""
            if "content" in msg and isinstance(msg["content"], str):
                content = msg["content"]
            elif "result" in msg and isinstance(msg["result"], str):
                content = msg["result"]
            if content:
                print(content)

    except NotImplementedError as e:
        print(f"[SDK] Error: {e}")
        return
    except KeyboardInterrupt:
        print("\n[SDK] Interrupted.")

    # Save session
    if messages:
        session_file = save_session(workspace_root, role, adapter_name, messages)
        print(f"\n[SDK] Session saved: {session_file}")
        print(f"[SDK] Messages: {len(messages)}")
    else:
        print("[SDK] No messages received.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch Socialware Agent (SDK mode)")
    parser.add_argument("--role", required=True, help="Role name")
    parser.add_argument("--adapter", default="claude", help="Platform adapter")
    parser.add_argument("--prompt", required=True, help="Prompt to send to the agent")
    args = parser.parse_args()

    # Workspace-local
    app_root = Path(__file__).parent.parent
    runtime_dir = app_root / ".runtime"

    if not runtime_dir.exists():
        print(f"Error: .runtime/ not found. Run 'make deploy' first.")
        sys.exit(1)

    project_dir = runtime_dir / "agents" / args.role.strip()
    if not project_dir.exists():
        print(f"Error: Role '{args.role}' not found at {project_dir}")
        sys.exit(1)

    adapter = load_adapter(args.adapter, project_dir)

    # Read workspace root
    ws_file = project_dir / ".workspace_root"
    workspace_root = Path(ws_file.read_text().strip()) if ws_file.exists() else app_root

    asyncio.run(run_sdk(adapter, args.prompt, workspace_root, args.role, args.adapter))


if __name__ == "__main__":
    main()
