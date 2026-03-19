#!/usr/bin/env python3
"""create-my-socialware — 创建新的 Socialware App 实例。

类似 mix phx.new 或 npx create-next-app。
将模板复制到 .socialware/workspace/{room}/{app}/ 并定制四原语。

Usage:
    uv run scripts/create-my-socialware.py
    uv run scripts/create-my-socialware.py --room my-team --app task-manager
    uv run scripts/create-my-socialware.py --room my-team --app task-manager --description "任务管理"
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent


def prompt_input(label: str, default: str = "") -> str:
    """交互式输入，支持默认值。"""
    if default:
        raw = input(f"  {label} [{default}]: ").strip()
        return raw or default
    while True:
        raw = input(f"  {label}: ").strip()
        if raw:
            return raw
        print("    (不能为空)")


def create_workspace(room: str, app: str, description: str) -> Path:
    """创建 workspace 并复制模板。"""
    workspace_dir = REPO_ROOT / ".socialware" / "workspace" / room / app
    if workspace_dir.exists():
        print(f"  Error: '{room}/{app}' already exists at {workspace_dir}")
        sys.exit(1)

    workspace_dir.mkdir(parents=True)

    # 复制 src/
    src_src = REPO_ROOT / "src"
    src_dst = workspace_dir / "src"
    if src_src.exists():
        shutil.copytree(src_src, src_dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        print(f"  Copied src/")

    # 复制 app/
    app_src = REPO_ROOT / "app"
    app_dst = workspace_dir / "app"
    if app_src.exists():
        shutil.copytree(app_src, app_dst, ignore=shutil.ignore_patterns("node_modules", ".next"))
        print(f"  Copied app/")

    # 复制 agent/ 四原语
    agent_src = REPO_ROOT / "agent"
    agent_dst = workspace_dir / "agent"
    agent_dst.mkdir()

    for primitive in ["role", "scope", "commitment", "flow"]:
        prim_src = agent_src / primitive
        prim_dst = agent_dst / primitive
        if prim_src.exists():
            shutil.copytree(prim_src, prim_dst, ignore=shutil.ignore_patterns("__pycache__", "README.md"))
            print(f"  Copied agent/{primitive}/")

    # 复制 deploy.sh, start.sh, adapters/
    for script in ["deploy.sh", "start.sh"]:
        script_src = agent_src / script
        script_dst = agent_dst / script
        if script_src.exists():
            shutil.copy2(script_src, script_dst)

    adapters_src = agent_src / "adapters"
    adapters_dst = agent_dst / "adapters"
    if adapters_src.exists():
        shutil.copytree(adapters_src, adapters_dst, ignore=shutil.ignore_patterns("__pycache__"))

    return workspace_dir


def customize_workspace(workspace_dir: Path, app: str, description: str) -> None:
    """定制 workspace 中的四原语。"""

    # 重写 scope/SOUL.md
    scope_soul = workspace_dir / "agent" / "scope" / "SOUL.md"
    scope_soul.write_text(f"""# {app}

{description}

## 能力

- 健康检查 (/health)
- (在此添加你的 App 能力)

## 边界

- (在此定义 Agent 的操作边界)
""")
    print(f"  Customized agent/scope/SOUL.md")

    # 重写 default role SOUL.md (保持 default，不重命名)
    role_soul = workspace_dir / "agent" / "role" / "default" / "SOUL.md"
    if role_soul.exists():
        role_soul.write_text(f"""# Default Agent

你是 {app} 的 Agent。

## 身份

- 角色: default
- 权限: 所有操作

## 职责

根据用户指令操作 {app}。
""")
        print(f"  Customized agent/role/default/SOUL.md")


def run_deploy(workspace_dir: Path) -> bool:
    """运行 deploy.sh。"""
    deploy_sh = REPO_ROOT / "agent" / "deploy.sh"

    result = subprocess.run(
        [str(deploy_sh), str(workspace_dir)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

    if result.returncode == 0:
        print(f"  Deploy complete")
        return True
    else:
        print(f"  Deploy failed: {result.stderr}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="创建新的 Socialware App 实例")
    parser.add_argument("--room", help="Room 名称 (workspace 分组)")
    parser.add_argument("--app", help="App 名称")
    parser.add_argument("--description", help="App 描述")
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

    # 1. 创建并复制
    workspace_dir = create_workspace(room, app, description)
    print()

    # 2. 定制
    customize_workspace(workspace_dir, app, description)
    print()

    # 3. Deploy
    run_deploy(workspace_dir)

    ws_rel = f".socialware/workspace/{room}/{app}"
    print()
    print("=" * 40)
    print(f"Created '{room}/{app}' at {ws_rel}/")
    print()
    print("Next steps:")
    print(f"  # 启动 agent (开发模式)")
    print(f"  ./agent/start.sh --role default --workspace {ws_rel}")
    print()
    print(f"  # 编辑四原语")
    print(f"  vim {ws_rel}/agent/scope/SOUL.md")
    print(f"  vim {ws_rel}/agent/role/default/SOUL.md")
    print(f"  vim {ws_rel}/agent/flow/")
    print()
    print(f"  # 添加新角色 (P5 渐进生长)")
    print(f"  mkdir {ws_rel}/agent/role/admin")
    print(f"  vim {ws_rel}/agent/role/admin/SOUL.md")
    print()


if __name__ == "__main__":
    main()
