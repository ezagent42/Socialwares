"""测试 evolve 机制。"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
EVOLVE_SH = REPO_ROOT / "scripts" / "evolve.sh"
CREATE_SCRIPT = REPO_ROOT / "scripts" / "create-my-socialware.py"


@pytest.fixture
def workspace(tmp_path):
    """创建一个 test workspace 用于 evolve 测试。"""
    ws_name = "evolve-test"
    ws_dir = REPO_ROOT / ".socialware" / "workspace" / ws_name

    # 创建 workspace
    result = subprocess.run(
        [sys.executable, str(CREATE_SCRIPT),
         "--name", ws_name, "--description", "Evolve Test", "--role", "default"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"Create failed: {result.stderr}"

    yield ws_name, ws_dir

    # 清理
    if ws_dir.exists():
        shutil.rmtree(ws_dir)


class TestEvolve:
    """测试 evolve 机制。"""

    def test_evolve_script_exists(self):
        assert EVOLVE_SH.exists()
        assert os.access(str(EVOLVE_SH), os.X_OK)

    def test_evolve_no_changes(self, workspace):
        """模板内容同步后应报告 no changes。"""
        ws_name, ws_dir = workspace

        # create-my-socialware 会定制 SOUL.md，所以和模板不同。
        # 手动同步回模板内容，模拟"无变更"场景。
        for primitive in ["role", "scope", "commitment", "flow"]:
            src = REPO_ROOT / "agent" / primitive
            dst = ws_dir / "agent" / primitive
            if src.exists() and dst.exists():
                shutil.rmtree(dst)
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("README.md"))

        result = subprocess.run(
            [str(EVOLVE_SH), ws_name, "--check"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        assert "No changes" in result.stdout

    def test_evolve_detects_agent_changes(self, workspace):
        """修改 workspace 的 agent/ 后应检测到变更。"""
        ws_name, ws_dir = workspace

        # 修改 workspace 的 scope/SOUL.md
        soul_path = ws_dir / "agent" / "scope" / "SOUL.md"
        soul_path.write_text("# Modified\n\nThis scope has been evolved.\n")

        result = subprocess.run(
            [str(EVOLVE_SH), ws_name, "--check"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        assert "Changes detected" in result.stdout
        assert "agent/scope" in result.stdout

    def test_evolve_nonexistent_workspace(self):
        """不存在的 workspace 应报错。"""
        result = subprocess.run(
            [str(EVOLVE_SH), "nonexistent", "--check"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode != 0
