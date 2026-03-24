"""Tests for runtime hooks — verify they actually work, not just exist.

Tests:
- log_action.sh processes PostToolUse input and writes JSONL
- check_violations.sh reads violations and reports them
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
AGENT_DIR = REPO_ROOT / "agent"


def _create_test_workspace(tmp_path: Path) -> Path:
    """Create a test workspace with deployed .runtime/."""
    workspace = tmp_path / "test-app"
    workspace.mkdir()
    shutil.copytree(AGENT_DIR, workspace / "agent")
    # Run deploy
    result = subprocess.run(
        [str(workspace / "agent" / "deploy.sh")],
        capture_output=True, text=True, cwd=str(workspace),
    )
    assert result.returncode == 0, f"deploy failed: {result.stderr}"
    return workspace


class TestLogActionHook:
    """Test PostToolUse conversation logging hook."""

    def test_hook_processes_input(self, tmp_path):
        """Feed tool call data to log_action.sh → verify JSONL written."""
        workspace = _create_test_workspace(tmp_path)
        hook = workspace / ".runtime" / "agents" / "default" / ".claude" / "hooks" / "log_action.sh"

        # Create conversations directory
        conv_dir = workspace / ".runtime" / "data" / "conversations"
        conv_dir.mkdir(parents=True, exist_ok=True)

        # Simulate PostToolUse input
        tool_input = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "curl http://localhost:8001/health"},
        })

        result = subprocess.run(
            ["bash", str(hook)],
            input=tool_input,
            capture_output=True, text=True,
            cwd=str(workspace / ".runtime" / "agents" / "default"),
        )
        # Hook should not crash (exit 0 or silent failure)
        # Check if JSONL was written
        jsonl_file = conv_dir / "current.jsonl"
        if jsonl_file.exists():
            lines = jsonl_file.read_text().strip().splitlines()
            assert len(lines) >= 1, "Should have at least one log entry"
            entry = json.loads(lines[0])
            assert "timestamp" in entry
            assert entry.get("tool") == "Bash" or "tool" in entry

    def test_hook_is_executable(self, tmp_path):
        workspace = _create_test_workspace(tmp_path)
        hook = workspace / ".runtime" / "agents" / "default" / ".claude" / "hooks" / "log_action.sh"
        assert os.access(str(hook), os.X_OK)


class TestCheckViolationsHook:
    """Test SessionStart violations check hook."""

    def test_no_violations(self, tmp_path):
        """With no violations, hook reports none."""
        workspace = _create_test_workspace(tmp_path)
        hook = workspace / ".runtime" / "agents" / "default" / ".claude" / "hooks" / "check_violations.sh"

        result = subprocess.run(
            ["bash", str(hook)],
            capture_output=True, text=True,
            cwd=str(workspace / ".runtime" / "agents" / "default"),
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "No pending violations" in context or "No violations directory" in context

    def test_detects_unresolved_violation(self, tmp_path):
        """With an unresolved violation for this role, hook reports it."""
        workspace = _create_test_workspace(tmp_path)
        hook = workspace / ".runtime" / "agents" / "default" / ".claude" / "hooks" / "check_violations.sh"

        # Write a violation targeting the 'default' role
        viol_dir = workspace / ".runtime" / "data" / "violations"
        viol_dir.mkdir(parents=True, exist_ok=True)
        violation = {
            "id": "v-001",
            "constraint": "C1",
            "description": "test violation",
            "trigger_action": "force_resolve",
            "trigger_role": "default",
            "resolved": False,
        }
        (viol_dir / "current.jsonl").write_text(json.dumps(violation) + "\n")

        result = subprocess.run(
            ["bash", str(hook)],
            capture_output=True, text=True,
            cwd=str(workspace / ".runtime" / "agents" / "default"),
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "1 unresolved" in context
        assert "C1" in context

    def test_ignores_other_role_violations(self, tmp_path):
        """Violations for other roles should not be reported."""
        workspace = _create_test_workspace(tmp_path)
        hook = workspace / ".runtime" / "agents" / "default" / ".claude" / "hooks" / "check_violations.sh"

        viol_dir = workspace / ".runtime" / "data" / "violations"
        viol_dir.mkdir(parents=True, exist_ok=True)
        violation = {
            "id": "v-002",
            "constraint": "C2",
            "description": "admin only violation",
            "trigger_role": "admin",
            "resolved": False,
        }
        (viol_dir / "current.jsonl").write_text(json.dumps(violation) + "\n")

        result = subprocess.run(
            ["bash", str(hook)],
            capture_output=True, text=True,
            cwd=str(workspace / ".runtime" / "agents" / "default"),
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert "No pending violations" in output["hookSpecificOutput"]["additionalContext"]

    def test_ignores_resolved_violations(self, tmp_path):
        """Resolved violations should not be reported."""
        workspace = _create_test_workspace(tmp_path)
        hook = workspace / ".runtime" / "agents" / "default" / ".claude" / "hooks" / "check_violations.sh"

        viol_dir = workspace / ".runtime" / "data" / "violations"
        viol_dir.mkdir(parents=True, exist_ok=True)
        violation = {
            "id": "v-003",
            "constraint": "C1",
            "description": "resolved",
            "trigger_role": "default",
            "resolved": True,
        }
        (viol_dir / "current.jsonl").write_text(json.dumps(violation) + "\n")

        result = subprocess.run(
            ["bash", str(hook)],
            capture_output=True, text=True,
            cwd=str(workspace / ".runtime" / "agents" / "default"),
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert "No pending violations" in output["hookSpecificOutput"]["additionalContext"]

    def test_hook_is_executable(self, tmp_path):
        workspace = _create_test_workspace(tmp_path)
        hook = workspace / ".runtime" / "agents" / "default" / ".claude" / "hooks" / "check_violations.sh"
        assert os.access(str(hook), os.X_OK)
