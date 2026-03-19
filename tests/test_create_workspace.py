"""测试 create-my-socialware 工作流。"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
CREATE_SCRIPT = REPO_ROOT / "scripts" / "create-my-socialware.py"


class TestCreateWorkspace:
    """测试 create-my-socialware 脚本。"""

    def test_script_exists(self):
        assert CREATE_SCRIPT.exists()

    def test_create_workspace_with_args(self):
        """使用命令行参数创建 workspace (room/app 结构)。"""
        room = "test-room"
        app = "test-app"
        workspace_dir = REPO_ROOT / ".socialware" / "workspace" / room / app

        try:
            result = subprocess.run(
                [
                    sys.executable, str(CREATE_SCRIPT),
                    "--room", room,
                    "--app", app,
                    "--description", "Test App",
                ],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )

            assert result.returncode == 0, f"Failed:\n{result.stderr}\n{result.stdout}"

            # 检查目录结构
            assert workspace_dir.exists()
            assert (workspace_dir / "src").is_dir()
            assert (workspace_dir / "agent").is_dir()
            assert (workspace_dir / "agent" / "scope" / "SOUL.md").exists()
            assert (workspace_dir / "agent" / "role" / "default" / "SOUL.md").exists()
            assert (workspace_dir / "agent" / "flow").is_dir()
            assert (workspace_dir / "agent" / "commitment").is_dir()

            # 检查定制内容
            scope_soul = (workspace_dir / "agent" / "scope" / "SOUL.md").read_text()
            assert app in scope_soul

            role_soul = (workspace_dir / "agent" / "role" / "default" / "SOUL.md").read_text()
            assert app in role_soul

            # 检查 .runtime/ 被创建 (deploy 成功)
            assert (workspace_dir / ".runtime").is_dir()
            assert (workspace_dir / ".runtime" / "agents" / "default").is_dir()

        finally:
            room_dir = REPO_ROOT / ".socialware" / "workspace" / room
            if room_dir.exists():
                shutil.rmtree(room_dir)

    def test_duplicate_workspace_fails(self):
        """重复创建相同 room/app 应失败。"""
        room = "dup-room"
        app = "dup-app"
        room_dir = REPO_ROOT / ".socialware" / "workspace" / room

        try:
            r1 = subprocess.run(
                [sys.executable, str(CREATE_SCRIPT),
                 "--room", room, "--app", app, "--description", "Test"],
                capture_output=True, text=True, cwd=str(REPO_ROOT),
            )
            assert r1.returncode == 0

            r2 = subprocess.run(
                [sys.executable, str(CREATE_SCRIPT),
                 "--room", room, "--app", app, "--description", "Test"],
                capture_output=True, text=True, cwd=str(REPO_ROOT),
            )
            assert r2.returncode != 0

        finally:
            if room_dir.exists():
                shutil.rmtree(room_dir)
