"""Tests for the evolve mechanism."""
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
def workspace():
    """Create a test workspace for evolve tests."""
    room = "evolve-room"
    app = "evolve-app"
    ws_path = f"{room}/{app}"
    ws_dir = REPO_ROOT / ".socialware" / "workspace" / room / app

    result = subprocess.run(
        [sys.executable, str(CREATE_SCRIPT),
         "--room", room, "--app", app, "--description", "Evolve Test"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"Create failed: {result.stderr}\n{result.stdout}"

    yield ws_path, ws_dir

    room_dir = REPO_ROOT / ".socialware" / "workspace" / room
    if room_dir.exists():
        shutil.rmtree(room_dir)


class TestEvolve:
    """Tests for the evolve mechanism."""

    def test_evolve_script_exists(self):
        assert EVOLVE_SH.exists()
        assert os.access(str(EVOLVE_SH), os.X_OK)

    def test_evolve_no_changes(self, workspace):
        """Should report no changes after syncing template content."""
        ws_path, ws_dir = workspace

        # create-my-socialware customizes SOUL.md, so manually sync back to template content
        for primitive in ["role", "scope", "commitment", "flow"]:
            src = REPO_ROOT / "agent" / primitive
            dst = ws_dir / "agent" / primitive
            if src.exists() and dst.exists():
                shutil.rmtree(dst)
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("README.md"))

        result = subprocess.run(
            [str(EVOLVE_SH), ws_path, "--check"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        assert "No changes" in result.stdout

    def test_evolve_detects_agent_changes(self, workspace):
        """Should detect changes after modifying the workspace's agent/ directory."""
        ws_path, ws_dir = workspace

        soul_path = ws_dir / "agent" / "scope" / "SOUL.md"
        soul_path.write_text("# Modified\n\nThis scope has been evolved.\n")

        result = subprocess.run(
            [str(EVOLVE_SH), ws_path, "--check"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        assert "Changes detected" in result.stdout
        assert "agent/scope" in result.stdout

    def test_evolve_nonexistent_workspace(self):
        """A nonexistent workspace should return an error."""
        result = subprocess.run(
            [str(EVOLVE_SH), "nonexistent/app", "--check"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode != 0
