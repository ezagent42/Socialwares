"""CLI 测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from socialwares.cli import main, _deep_merge, _get_agent_workspace


@pytest.fixture
def runner():
    return CliRunner()


class TestNew:
    def test_new_creates_project(self, runner, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(main, ["new", "my-app"])
        assert result.exit_code == 0
        assert "Created my-app/" in result.output
        assert (tmp_path / "my-app" / "socialware.py").is_file()
        assert (tmp_path / "my-app" / "agent" / "role" / "default.md").is_file()
        assert (tmp_path / "my-app" / "agent" / "scope" / "scope.md").is_file()
        assert (tmp_path / "my-app" / "agent" / "flow" / "check_health" / "SKILL.md").is_file()

    def test_new_renders_app_name(self, runner, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(main, ["new", "my-app"])
        content = (tmp_path / "my-app" / "socialware.py").read_text()
        assert 'App("my-app")' in content
        assert "{{APP_NAME}}" not in content

    def test_new_existing_dir_fails(self, runner, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "my-app").mkdir()
        result = runner.invoke(main, ["new", "my-app"])
        assert result.exit_code != 0
        assert "already exists" in result.output


class TestDeploy:
    def test_deploy_compiles(self, runner, tmp_path, monkeypatch) -> None:
        # 先 new，再 deploy
        monkeypatch.chdir(tmp_path)
        runner.invoke(main, ["new", "test-app"])
        monkeypatch.chdir(tmp_path / "test-app")
        result = runner.invoke(main, ["deploy"])
        assert result.exit_code == 0
        assert "Compiled test-app" in result.output
        assert (tmp_path / "test-app" / ".runtime" / "agents" / "default").is_dir()

    def test_deploy_no_socialware_py(self, runner, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(main, ["deploy"])
        assert result.exit_code != 0
        assert "socialware.py not found" in result.output


class TestDeepMerge:
    def test_simple_merge(self) -> None:
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        assert _deep_merge(base, override) == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self) -> None:
        base = {"permissions": {"allow": ["read"]}}
        override = {"hooks": {"UserPromptSubmit": [{"type": "command"}]}}
        result = _deep_merge(base, override)
        assert result["permissions"]["allow"] == ["read"]
        assert "UserPromptSubmit" in result["hooks"]

    def test_deep_nested_merge(self) -> None:
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"d": 3, "e": 4}}}
        result = _deep_merge(base, override)
        assert result == {"a": {"b": {"c": 1, "d": 3, "e": 4}}}


class TestAssignMock:
    def test_mock_workspace(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("socialwares.cli._workspace_root", lambda: tmp_path)
        workspace = _get_agent_workspace("test-agent", "#test")
        assert workspace.is_dir()
        assert (workspace / ".claude" / "settings.local.json").is_file()
        settings = json.loads((workspace / ".claude" / "settings.local.json").read_text())
        assert "permissions" in settings
        # 路径应该是 {workspace_root}/test/agents/test-agent
        assert "test" in str(workspace)
        assert "agents" in str(workspace)
