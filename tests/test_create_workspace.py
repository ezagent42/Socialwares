"""Tests for create-my-socialware workflow.

Verifies:
- Workspace created with correct structure
- Four primitives copied and customized
- deploy.sh and start.sh copied (workspace is self-contained)
- No auto-deploy (user deploys manually after editing)
- Duplicate workspace detection
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
CREATE_SCRIPT = REPO_ROOT / "scripts" / "create-my-socialware.py"


class TestCreateWorkspace:
    """Test create-my-socialware script."""

    def test_script_exists(self):
        assert CREATE_SCRIPT.exists()

    def test_create_workspace_with_args(self):
        """Create workspace with room/app structure."""
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

            # Check directory structure
            assert workspace_dir.exists()
            assert (workspace_dir / "src").is_dir()
            assert (workspace_dir / "agent").is_dir()
            assert (workspace_dir / "agent" / "scope" / "scope.md").exists()
            assert (workspace_dir / "agent" / "role" / "default.md").exists()
            assert (workspace_dir / "agent" / "flow").is_dir()
            assert (workspace_dir / "agent" / "commitment").is_dir()

            # Check deploy.sh and start.sh are copied (self-contained)
            assert (workspace_dir / "agent" / "deploy.sh").exists()
            assert (workspace_dir / "agent" / "start.sh").exists()
            assert (workspace_dir / "agent" / "adapters").is_dir()

            # Check customized content
            scope_soul = (workspace_dir / "agent" / "scope" / "scope.md").read_text()
            assert app in scope_soul

            role_soul = (workspace_dir / "agent" / "role" / "default.md").read_text()
            assert app in role_soul

            # Check Makefile copied
            assert (workspace_dir / "Makefile").exists(), "Makefile should be copied to workspace"
            makefile_content = (workspace_dir / "Makefile").read_text()
            assert "deploy" in makefile_content

            # Check auto-deploy ran (.runtime/ should exist)
            assert (workspace_dir / ".runtime").is_dir(), \
                ".runtime/ should exist — create runs initial deploy"
            assert (workspace_dir / ".runtime" / "agents" / "default").is_dir()

            # Check pyproject.toml copied with app name
            pyproject = (workspace_dir / "pyproject.toml").read_text()
            assert app in pyproject

        finally:
            room_dir = REPO_ROOT / ".socialware" / "workspace" / room
            if room_dir.exists():
                shutil.rmtree(room_dir)

    def test_duplicate_workspace_fails(self):
        """Creating duplicate room/app should fail."""
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
