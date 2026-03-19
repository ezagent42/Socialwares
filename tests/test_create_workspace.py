"""测试 create-my-socialware 工作流。"""
from __future__ import annotations

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

    def test_create_workspace_with_args(self, tmp_path, monkeypatch):
        """使用命令行参数创建 workspace。"""
        # 临时修改 REPO_ROOT
        monkeypatch.chdir(REPO_ROOT)

        # 直接导入并调用
        sys.path.insert(0, str(CREATE_SCRIPT.parent))
        import importlib.util
        spec = importlib.util.spec_from_file_location("create_my_socialware", CREATE_SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        # 修改 REPO_ROOT 为 tmp_path 模拟
        original_root = REPO_ROOT

        # 使用 subprocess 更简单
        workspace_name = "test-app"
        workspace_dir = REPO_ROOT / ".socialware" / "workspace" / workspace_name

        try:
            result = subprocess.run(
                [
                    sys.executable, str(CREATE_SCRIPT),
                    "--name", workspace_name,
                    "--description", "Test App",
                    "--role", "admin",
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
            assert (workspace_dir / "agent" / "role" / "admin" / "SOUL.md").exists()
            assert (workspace_dir / "agent" / "flow").is_dir()
            assert (workspace_dir / "agent" / "commitment").is_dir()

            # 检查定制内容
            scope_soul = (workspace_dir / "agent" / "scope" / "SOUL.md").read_text()
            assert "test-app" in scope_soul

            role_soul = (workspace_dir / "agent" / "role" / "admin" / "SOUL.md").read_text()
            assert "admin" in role_soul.lower()

            # 检查 .runtime/ 被创建 (deploy 成功)
            assert (workspace_dir / ".runtime").is_dir()
            assert (workspace_dir / ".runtime" / "agents" / "admin").is_dir()

        finally:
            # 清理
            import shutil
            if workspace_dir.exists():
                shutil.rmtree(workspace_dir)

    def test_duplicate_workspace_fails(self, monkeypatch):
        """重复创建相同名称的 workspace 应失败。"""
        workspace_name = "duplicate-test"
        workspace_dir = REPO_ROOT / ".socialware" / "workspace" / workspace_name

        try:
            # 第一次创建
            r1 = subprocess.run(
                [sys.executable, str(CREATE_SCRIPT),
                 "--name", workspace_name, "--description", "Test", "--role", "default"],
                capture_output=True, text=True, cwd=str(REPO_ROOT),
            )
            assert r1.returncode == 0

            # 第二次应失败
            r2 = subprocess.run(
                [sys.executable, str(CREATE_SCRIPT),
                 "--name", workspace_name, "--description", "Test", "--role", "default"],
                capture_output=True, text=True, cwd=str(REPO_ROOT),
            )
            assert r2.returncode != 0

        finally:
            import shutil
            if workspace_dir.exists():
                shutil.rmtree(workspace_dir)
