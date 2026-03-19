#!/usr/bin/env python3
"""生产模式 Agent 启动入口。

App 后端调用此脚本，通过 adapter 以 SDK 模式启动 agent。
与 agent/start.sh (开发模式 Shell 启动) 互补，不冲突。

Usage:
    python src/start_agent.py --role admin
    python src/start_agent.py --role admin,reviewer
    python src/start_agent.py --role admin --adapter codex
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path


def load_adapter(adapter_name: str, project_dir: Path):
    """动态加载指定平台的 adapter。"""
    adapter_path = Path(__file__).parent.parent / "agent" / "adapters"
    sys.path.insert(0, str(adapter_path))
    sys.path.insert(0, str(adapter_path / adapter_name))

    from base import RoleConfig

    config = RoleConfig.from_runtime(project_dir)

    # 动态导入 adapter 模块
    mod = importlib.import_module(f"{adapter_name}.sdk")

    # 找到 BaseAdapter 的子类
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
    parser = argparse.ArgumentParser(description="启动 Socialware Agent (生产模式)")
    parser.add_argument("--role", required=True, help="Role name(s), comma-separated")
    parser.add_argument("--adapter", default="claude", help="Platform adapter")
    parser.add_argument(
        "--workspace",
        default=".socialware/workspace/default",
        help="Workspace path",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    runtime_dir = repo_root / args.workspace / ".runtime"

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
