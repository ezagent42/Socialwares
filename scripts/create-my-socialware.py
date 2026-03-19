#!/usr/bin/env python3
"""create-my-socialware — 创建新的 Socialware App 实例。

类似 mix phx.new 或 npx create-next-app。
将模板复制到 .socialware/workspace/{name}/ 并定制四原语。

Usage:
    uv run scripts/create-my-socialware.py
    uv run scripts/create-my-socialware.py --name my-app --role admin --description "我的应用"
"""
from __future__ import annotations

import argparse
import os
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


def create_workspace(
    name: str,
    description: str,
    role: str,
) -> Path:
    """创建 workspace 并复制模板。"""
    workspace_dir = REPO_ROOT / ".socialware" / "workspace" / name
    if workspace_dir.exists():
        print(f"  Error: workspace '{name}' already exists at {workspace_dir}")
        sys.exit(1)

    workspace_dir.mkdir(parents=True)

    # 复制 src/
    src_src = REPO_ROOT / "src"
    src_dst = workspace_dir / "src"
    if src_src.exists():
        shutil.copytree(src_src, src_dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        print(f"  Copied src/ → {src_dst.relative_to(REPO_ROOT)}")

    # 复制 app/
    app_src = REPO_ROOT / "app"
    app_dst = workspace_dir / "app"
    if app_src.exists():
        shutil.copytree(app_src, app_dst, ignore=shutil.ignore_patterns("node_modules", ".next"))
        print(f"  Copied app/ → {app_dst.relative_to(REPO_ROOT)}")

    # 复制 agent/ (不含 adapters/ 和脚本，只复制四原语)
    agent_src = REPO_ROOT / "agent"
    agent_dst = workspace_dir / "agent"
    agent_dst.mkdir()

    for primitive in ["role", "scope", "commitment", "flow"]:
        prim_src = agent_src / primitive
        prim_dst = agent_dst / primitive
        if prim_src.exists():
            shutil.copytree(prim_src, prim_dst, ignore=shutil.ignore_patterns("__pycache__", "README.md"))
            print(f"  Copied agent/{primitive}/ → {prim_dst.relative_to(REPO_ROOT)}")

    # 复制 deploy.sh 和 start.sh (需要在 workspace 内可执行)
    for script in ["deploy.sh", "start.sh"]:
        script_src = agent_src / script
        script_dst = agent_dst / script
        if script_src.exists():
            shutil.copy2(script_src, script_dst)

    # 复制 adapters/
    adapters_src = agent_src / "adapters"
    adapters_dst = agent_dst / "adapters"
    if adapters_src.exists():
        shutil.copytree(adapters_src, adapters_dst, ignore=shutil.ignore_patterns("__pycache__"))

    return workspace_dir


def customize_workspace(workspace_dir: Path, name: str, description: str, role: str) -> None:
    """定制 workspace 中的四原语。"""

    # 1. 重写 scope/SOUL.md
    scope_soul = workspace_dir / "agent" / "scope" / "SOUL.md"
    scope_soul.write_text(f"""# {name}

{description}

## 能力

- 健康检查 (/health)
- (在此添加你的 App 能力)

## 边界

- (在此定义 Agent 的操作边界)
""")
    print(f"  Customized agent/scope/SOUL.md")

    # 2. 重命名 role: default → 用户指定的 role
    old_role = workspace_dir / "agent" / "role" / "default"
    new_role = workspace_dir / "agent" / "role" / role
    if old_role.exists() and role != "default":
        old_role.rename(new_role)

    # 重写 role SOUL.md
    role_soul = new_role if new_role.exists() else old_role
    (role_soul / "SOUL.md").write_text(f"""# {role.capitalize()} Agent

你是 {name} 的 {role} Agent。

## 身份

- 角色: {role}
- 权限: 所有操作

## 职责

根据用户指令操作 {name}。
""")
    print(f"  Customized agent/role/{role}/SOUL.md")


def run_deploy(workspace_dir: Path) -> bool:
    """运行 deploy.sh。"""
    deploy_sh = workspace_dir / "agent" / "deploy.sh"
    if not deploy_sh.exists():
        # fallback: 使用模板的 deploy.sh
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
    parser.add_argument("--name", help="项目名称")
    parser.add_argument("--description", help="项目描述")
    parser.add_argument("--role", help="初始角色名称")
    args = parser.parse_args()

    print()
    print("create-my-socialware")
    print("=" * 40)
    print()

    name = args.name or prompt_input("Project name")
    description = args.description or prompt_input("Description", f"{name} Socialware App")
    role = args.role or prompt_input("Initial role", "default")

    print()
    print(f"Creating {name}...")
    print()

    # 1. 创建并复制
    workspace_dir = create_workspace(name, description, role)

    print()

    # 2. 定制
    customize_workspace(workspace_dir, name, description, role)

    print()

    # 3. Deploy
    run_deploy(workspace_dir)

    print()
    print("=" * 40)
    print(f"Created '{name}' at .socialware/workspace/{name}/")
    print()
    print("Next steps:")
    print(f"  # 启动 agent (开发模式)")
    print(f"  ./agent/start.sh --role {role} --workspace .socialware/workspace/{name}")
    print()
    print(f"  # 编辑四原语")
    print(f"  vim .socialware/workspace/{name}/agent/scope/SOUL.md")
    print(f"  vim .socialware/workspace/{name}/agent/role/{role}/SOUL.md")
    print(f"  vim .socialware/workspace/{name}/agent/flow/")
    print()


if __name__ == "__main__":
    main()
