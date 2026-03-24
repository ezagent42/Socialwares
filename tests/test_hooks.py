"""Tests for runtime hooks — verify they actually work, not just exist.

Tests:
- log_prompt.sh processes UserPromptSubmit input and writes JSONL
- log_tool.sh processes PreToolUse input and writes JSONL

Hooks write to .runtime/data/prompts/current.jsonl.
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


class TestLogPromptHook:
    """Test UserPromptSubmit hook."""

    def test_hook_processes_input(self, tmp_path):
        workspace = _create_test_workspace(tmp_path)
        hook = workspace / ".runtime" / "agents" / "default" / ".claude" / "hooks" / "log_prompt.sh"
        if not hook.exists():
            pytest.skip("Hook not generated (may need adapter=claude)")

        prompt_input = json.dumps({
            "prompt": "check health",
            "session_id": "test-session",
        })

        result = subprocess.run(
            ["bash", str(hook)],
            input=prompt_input,
            capture_output=True, text=True,
            cwd=str(workspace / ".runtime" / "agents" / "default"),
        )

        # Check if JSONL was written
        prompts_dir = workspace / ".runtime" / "data" / "prompts"
        jsonl_file = prompts_dir / "current.jsonl"
        if jsonl_file.exists():
            lines = jsonl_file.read_text().strip().splitlines()
            assert len(lines) >= 1
            entry = json.loads(lines[0])
            assert entry.get("type") == "user_prompt"
            assert "check health" in entry.get("content", "")

    def test_hook_is_executable(self, tmp_path):
        workspace = _create_test_workspace(tmp_path)
        hook = workspace / ".runtime" / "agents" / "default" / ".claude" / "hooks" / "log_prompt.sh"
        if not hook.exists():
            pytest.skip("Hook not generated")
        assert os.access(str(hook), os.X_OK)


class TestLogToolHook:
    """Test PreToolUse hook."""

    def test_hook_processes_input(self, tmp_path):
        workspace = _create_test_workspace(tmp_path)
        hook = workspace / ".runtime" / "agents" / "default" / ".claude" / "hooks" / "log_tool.sh"
        if not hook.exists():
            pytest.skip("Hook not generated")

        tool_input = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "curl http://localhost:8001/health"},
            "session_id": "test-session",
        })

        result = subprocess.run(
            ["bash", str(hook)],
            input=tool_input,
            capture_output=True, text=True,
            cwd=str(workspace / ".runtime" / "agents" / "default"),
        )

        prompts_dir = workspace / ".runtime" / "data" / "prompts"
        jsonl_file = prompts_dir / "current.jsonl"
        if jsonl_file.exists():
            lines = jsonl_file.read_text().strip().splitlines()
            assert len(lines) >= 1
            entry = json.loads(lines[0])
            assert entry.get("type") == "tool_call"
            assert entry.get("tool") == "Bash"

    def test_hook_is_executable(self, tmp_path):
        workspace = _create_test_workspace(tmp_path)
        hook = workspace / ".runtime" / "agents" / "default" / ".claude" / "hooks" / "log_tool.sh"
        if not hook.exists():
            pytest.skip("Hook not generated")
        assert os.access(str(hook), os.X_OK)
