"""CLI tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml
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
        # First new, then deploy
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


class TestEject:
    def test_eject_copies_builtin_skill(self, runner, tmp_path, monkeypatch) -> None:
        """eject copies a built-in skill to agent/flow/ for customization."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(main, ["new", "test-app"])
        monkeypatch.chdir(tmp_path / "test-app")

        result = runner.invoke(main, ["eject", "evolve_structure_check"])
        assert result.exit_code == 0
        assert "Ejected" in result.output

        ejected = tmp_path / "test-app" / "agent" / "flow" / "evolve_structure_check"
        assert ejected.is_dir()
        assert not ejected.is_symlink()
        assert (ejected / "SKILL.md").is_file()

    def test_eject_unknown_skill_fails(self, runner, tmp_path, monkeypatch) -> None:
        """eject with a non-existent built-in skill should fail."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(main, ["new", "test-app"])
        monkeypatch.chdir(tmp_path / "test-app")

        result = runner.invoke(main, ["eject", "nonexistent_skill"])
        assert result.exit_code != 0
        assert "not a built-in skill" in result.output

    def test_eject_already_exists_fails(self, runner, tmp_path, monkeypatch) -> None:
        """eject should fail if skill dir already exists as a real directory."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(main, ["new", "test-app"])
        monkeypatch.chdir(tmp_path / "test-app")

        # First eject succeeds
        runner.invoke(main, ["eject", "evolve_structure_check"])
        # Second eject should fail (already exists, not a symlink)
        result = runner.invoke(main, ["eject", "evolve_structure_check"])
        assert result.exit_code != 0
        assert "already exists" in result.output


class TestNewFrom:
    def _make_source_project(self, tmp_path: Path) -> Path:
        """Create a minimal source project to clone from."""
        src = tmp_path / "source-app"
        (src / "agent" / "role").mkdir(parents=True)
        (src / "agent" / "scope").mkdir(parents=True)
        (src / "agent" / "flow" / "check_health").mkdir(parents=True)
        (src / "agent" / "flow" / "check_health" / "SKILL.md").write_text("# Check Health")
        (src / "agent" / "scope" / "scope.md").write_text("# Scope")
        (src / "agent" / "role" / "default.md").write_text("# Default")
        (src / "socialware.py").write_text(
            'from socialwares import App\n'
            'app = App("source-app")\n'
            'app.scope(file="agent/scope/scope.md")\n'
            'app.role("default", file="agent/role/default.md")\n'
            'app.action("check_health", role=["default"])\n'
        )
        (src / "pyproject.toml").write_text(
            '[project]\nname = "source-app"\nversion = "0.1.0"\n\n[tool.socialwares]\n'
        )
        # Add a .git directory to verify it gets removed
        (src / ".git").mkdir()
        (src / ".git" / "HEAD").write_text("ref: refs/heads/main")
        # Add a stale symlink in agent/flow/ to verify it gets removed
        stale_link = src / "agent" / "flow" / "evolve_structure_check"
        stale_link.symlink_to("/nonexistent/path/that/does/not/exist")
        return src

    def test_new_from_local_creates_project(self, runner, tmp_path, monkeypatch) -> None:
        """new --from <local-path> creates the project directory."""
        src = self._make_source_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(main, ["new", "my-clone", "--from", str(src)])
        assert result.exit_code == 0
        assert "Created my-clone/" in result.output
        assert (tmp_path / "my-clone").is_dir()

    def test_new_from_replaces_app_name(self, runner, tmp_path, monkeypatch) -> None:
        """new --from replaces App name in socialware.py."""
        src = self._make_source_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        runner.invoke(main, ["new", "my-clone", "--from", str(src)])
        content = (tmp_path / "my-clone" / "socialware.py").read_text()
        assert 'App("my-clone")' in content
        assert 'App("source-app")' not in content

    def test_new_from_replaces_name_in_pyproject(self, runner, tmp_path, monkeypatch) -> None:
        """new --from replaces name in pyproject.toml."""
        src = self._make_source_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        runner.invoke(main, ["new", "my-clone", "--from", str(src)])
        content = (tmp_path / "my-clone" / "pyproject.toml").read_text()
        assert 'name = "my-clone"' in content
        assert 'name = "source-app"' not in content

    def test_new_from_removes_git_dir(self, runner, tmp_path, monkeypatch) -> None:
        """new --from removes .git/ directory (start fresh)."""
        src = self._make_source_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        runner.invoke(main, ["new", "my-clone", "--from", str(src)])
        assert not (tmp_path / "my-clone" / ".git").exists()

    def test_new_from_removes_stale_symlinks(self, runner, tmp_path, monkeypatch) -> None:
        """new --from removes stale symlinks in agent/flow/."""
        src = self._make_source_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        runner.invoke(main, ["new", "my-clone", "--from", str(src)])
        flow_dir = tmp_path / "my-clone" / "agent" / "flow"
        for item in flow_dir.iterdir():
            assert not item.is_symlink(), f"{item.name} should not be a symlink"
        # Real directories should be preserved
        assert (flow_dir / "check_health").is_dir()

    def test_new_from_existing_target_fails(self, runner, tmp_path, monkeypatch) -> None:
        """new --from should fail if target directory already exists."""
        src = self._make_source_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "my-clone").mkdir()
        result = runner.invoke(main, ["new", "my-clone", "--from", str(src)])
        assert result.exit_code != 0
        assert "already exists" in result.output


def _make_git_repo(tmp_path: Path) -> Path:
    """Create a minimal socialware project as a local git repo for install tests.

    Returns the path to the git repo directory.
    """
    import subprocess

    repo = tmp_path / "test-app-repo"
    (repo / "agent" / "role").mkdir(parents=True)
    (repo / "agent" / "scope").mkdir(parents=True)
    (repo / "agent" / "flow" / "check_health").mkdir(parents=True)
    (repo / "agent" / "flow" / "check_health" / "SKILL.md").write_text("# Check Health")
    (repo / "agent" / "scope" / "scope.md").write_text("# Scope")
    (repo / "agent" / "role" / "default.md").write_text("# Default")
    (repo / "socialware.py").write_text(
        'from socialwares import App\n'
        'app = App("test-app-repo")\n'
        'app.scope(file="agent/scope/scope.md")\n'
        'app.role("default", file="agent/role/default.md")\n'
        'app.action("check_health", role=["default"])\n'
    )
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "test-app-repo"\nversion = "0.1.0"\n\n[tool.socialwares]\n'
    )

    # Initialize as a real git repo so `git clone <local-path>` works
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo, check=True, capture_output=True,
    )
    return repo


class TestInstall:
    """Tests for the `socialwares install` CLI command."""

    def test_install_from_local_path(self, runner, tmp_path, monkeypatch) -> None:
        """install from a local git repo: app dir created, .runtime/ exists, installs.json updated."""
        repo = _make_git_repo(tmp_path)
        workspace = tmp_path / "workspace"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("socialwares.cli._workspace_root", lambda: workspace)

        result = runner.invoke(main, ["install", str(repo), "--channel", "#general"])
        assert result.exit_code == 0, result.output

        app_dir = workspace / "general" / "apps" / "test-app-repo"
        assert app_dir.is_dir(), "App directory should be created"
        assert (app_dir / ".runtime").is_dir(), "deploy should have produced .runtime/"
        assert (app_dir / "socialware.py").is_file()

        # installs.json should contain the entry
        installs = json.loads((workspace / "installs.json").read_text())
        assert len(installs) == 1
        assert installs[0]["app_name"] == "test-app-repo"
        assert installs[0]["channel"] == "#general"

    def test_install_already_installed(self, runner, tmp_path, monkeypatch) -> None:
        """Installing the same app twice should fail with an error message."""
        repo = _make_git_repo(tmp_path)
        workspace = tmp_path / "workspace"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("socialwares.cli._workspace_root", lambda: workspace)

        # First install
        r1 = runner.invoke(main, ["install", str(repo), "--channel", "#general"])
        assert r1.exit_code == 0, r1.output

        # Second install — should fail
        r2 = runner.invoke(main, ["install", str(repo), "--channel", "#general"])
        assert r2.exit_code != 0
        assert "already installed" in r2.output

    def test_install_stale_dir_cleanup(self, runner, tmp_path, monkeypatch) -> None:
        """If app dir exists but not in installs.json, it's cleaned up and reinstalled."""
        repo = _make_git_repo(tmp_path)
        workspace = tmp_path / "workspace"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("socialwares.cli._workspace_root", lambda: workspace)

        # Create stale directory (exists but no installs.json entry)
        stale_dir = workspace / "general" / "apps" / "test-app-repo"
        stale_dir.mkdir(parents=True)
        (stale_dir / "stale_marker.txt").write_text("I am stale")

        result = runner.invoke(main, ["install", str(repo), "--channel", "#general"])
        assert result.exit_code == 0, result.output
        assert "Cleaning up stale directory" in result.output

        # Stale marker should be gone (directory was cleaned and reinstalled)
        assert not (stale_dir / "stale_marker.txt").exists()
        # But the app should be properly installed
        assert (stale_dir / "socialware.py").is_file()
        assert (stale_dir / ".runtime").is_dir()

        installs = json.loads((workspace / "installs.json").read_text())
        assert len(installs) == 1
        assert installs[0]["app_name"] == "test-app-repo"


    def test_install_with_custom_path(self, runner, tmp_path, monkeypatch) -> None:
        """install with --path overrides the default install directory."""
        repo = _make_git_repo(tmp_path)
        workspace = tmp_path / "workspace"
        custom_dir = tmp_path / "custom" / "my-app"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("socialwares.cli._workspace_root", lambda: workspace)

        result = runner.invoke(
            main,
            ["install", str(repo), "--channel", "#general", "--path", str(custom_dir)],
        )
        assert result.exit_code == 0, result.output

        # App should be at custom path, not the default workspace path
        assert custom_dir.is_dir(), "App should be at custom path"
        assert (custom_dir / ".runtime").is_dir()
        assert (custom_dir / "socialware.py").is_file()

        default_dir = workspace / "general" / "apps" / "test-app-repo"
        assert not default_dir.exists(), "Default path should not be created"

        # installs.json should record the custom path
        installs = json.loads((workspace / "installs.json").read_text())
        assert len(installs) == 1
        assert installs[0]["app_dir"] == str(custom_dir)


class TestUninstall:
    """Tests for the `socialwares uninstall` CLI command."""

    def test_uninstall_removes_app(self, runner, tmp_path, monkeypatch) -> None:
        """install then uninstall: app dir removed and installs.json updated."""
        repo = _make_git_repo(tmp_path)
        workspace = tmp_path / "workspace"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("socialwares.cli._workspace_root", lambda: workspace)

        # Install first
        r1 = runner.invoke(main, ["install", str(repo), "--channel", "#dev"])
        assert r1.exit_code == 0, r1.output

        app_dir = workspace / "dev" / "apps" / "test-app-repo"
        assert app_dir.is_dir()

        # Uninstall
        r2 = runner.invoke(main, ["uninstall", "test-app-repo", "--channel", "#dev"])
        assert r2.exit_code == 0, r2.output
        assert "Uninstalled test-app-repo" in r2.output

        # installs.json should be empty
        installs = json.loads((workspace / "installs.json").read_text())
        assert len(installs) == 0

    def test_uninstall_nonexistent(self, runner, tmp_path, monkeypatch) -> None:
        """Uninstalling an app that's not installed should fail."""
        workspace = tmp_path / "workspace"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("socialwares.cli._workspace_root", lambda: workspace)

        result = runner.invoke(main, ["uninstall", "no-such-app", "--channel", "#dev"])
        assert result.exit_code != 0
        assert "not installed" in result.output


class TestList:
    """Tests for the `socialwares list` CLI command."""

    def test_list_empty(self, runner, tmp_path, monkeypatch) -> None:
        """No apps installed — should show 'No apps installed.' message."""
        workspace = tmp_path / "workspace"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("socialwares.cli._workspace_root", lambda: workspace)

        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "No apps installed" in result.output

    def test_list_with_apps(self, runner, tmp_path, monkeypatch) -> None:
        """After installing an app, it should appear in the list output."""
        repo = _make_git_repo(tmp_path)
        workspace = tmp_path / "workspace"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("socialwares.cli._workspace_root", lambda: workspace)

        # Install an app
        r1 = runner.invoke(main, ["install", str(repo), "--channel", "#general"])
        assert r1.exit_code == 0, r1.output

        # List should show it
        r2 = runner.invoke(main, ["list"])
        assert r2.exit_code == 0
        assert "test-app-repo" in r2.output
        assert "#general" in r2.output


class TestAssignMock:
    def test_mock_workspace(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("socialwares.cli._workspace_root", lambda: tmp_path)
        workspace = _get_agent_workspace("test-agent", "#test")
        assert workspace.is_dir()
        assert (workspace / ".claude" / "settings.local.json").is_file()
        settings = json.loads((workspace / ".claude" / "settings.local.json").read_text())
        assert "permissions" in settings
        # Path should be {workspace_root}/test/agents/test-agent
        assert "test" in str(workspace)
        assert "agents" in str(workspace)


class TestAssign:
    """Comprehensive tests for the ``assign`` command's merge logic.

    Setup pattern:
    1. ``socialwares new`` + ``socialwares deploy`` to produce ``.runtime/``
    2. Write ``installs.json`` under a mocked workspace root so
       ``_find_install_by_channel`` can locate the app.
    3. Monkeypatch ``_workspace_root`` so agent workspaces are created inside
       ``tmp_path`` (avoids touching ``~/.local/state``).
    4. Invoke ``assign`` via ``CliRunner``.
    """

    @pytest.fixture(autouse=True)
    def _setup_project(self, runner, tmp_path, monkeypatch):
        """Create a compiled project and wire up the workspace mock."""
        self.tmp = tmp_path
        self.runner = runner

        # -- create & compile the project --
        monkeypatch.chdir(tmp_path)
        res = runner.invoke(main, ["new", "test-app"])
        assert res.exit_code == 0, res.output

        self.app_dir = tmp_path / "test-app"
        monkeypatch.chdir(self.app_dir)
        res = runner.invoke(main, ["deploy"])
        assert res.exit_code == 0, res.output

        # -- mock workspace root inside tmp_path --
        self.ws_root = tmp_path / ".socialware" / "workspace"
        self.ws_root.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("socialwares.cli._workspace_root", lambda: self.ws_root)

        # -- write installs.json so _find_install_by_channel works --
        installs = [
            {
                "app_name": "test-app",
                "app_dir": str(self.app_dir),
                "channel": "#general",
                "roles": ["default", "dev", "evolver"],
            }
        ]
        (self.ws_root / "installs.json").write_text(json.dumps(installs, indent=2))

        self.channel = "#general"

    # ── helpers ──

    def _assign(self, agent: str, role: str) -> object:
        """Run ``socialwares assign`` and return the Click result."""
        return self.runner.invoke(
            main,
            ["assign", agent, "--role", role, "--channel", self.channel],
        )

    def _agent_workspace(self, agent: str) -> Path:
        """Return the local agent workspace path (mirrors ``_get_agent_workspace``)."""
        return self.ws_root / self.channel.lstrip("#") / "agents" / agent

    # ── 1. SOUL.md with source markers ──

    def test_assign_creates_soul_md_with_markers(self) -> None:
        """assign a role, verify SOUL.md contains source markers."""
        result = self._assign("bot-a", "default")
        assert result.exit_code == 0, result.output

        soul = self._agent_workspace("bot-a") / "SOUL.md"
        assert soul.is_file()
        content = soul.read_text()
        assert "<!-- socialware:test-app:default -->" in content
        assert "<!-- /socialware:test-app:default -->" in content

    # ── 2. Idempotent ──

    def test_assign_idempotent(self) -> None:
        """assign same role twice, verify SOUL.md has exactly one block."""
        self._assign("bot-a", "default")
        result = self._assign("bot-a", "default")
        assert result.exit_code == 0, result.output

        content = (self._agent_workspace("bot-a") / "SOUL.md").read_text()
        marker = "<!-- socialware:test-app:default -->"
        assert content.count(marker) == 1

    # ── 3. Multi-role same agent ──

    def test_assign_multi_role_same_agent(self) -> None:
        """assign default then evolver to same agent, verify two tagged blocks."""
        res1 = self._assign("bot-a", "default")
        assert res1.exit_code == 0, res1.output
        res2 = self._assign("bot-a", "evolver")
        assert res2.exit_code == 0, res2.output

        content = (self._agent_workspace("bot-a") / "SOUL.md").read_text()
        assert "<!-- socialware:test-app:default -->" in content
        assert "<!-- /socialware:test-app:default -->" in content
        assert "<!-- socialware:test-app:evolver -->" in content
        assert "<!-- /socialware:test-app:evolver -->" in content

    # ── 4. Skills symlinked ──

    def test_assign_skills_symlinked(self) -> None:
        """verify skills are symlinked to agent workspace's .claude/skills/."""
        result = self._assign("bot-a", "default")
        assert result.exit_code == 0, result.output

        skills_dir = self._agent_workspace("bot-a") / ".claude" / "skills"
        # The default role has at least check_health
        runtime_skills = (
            self.app_dir / ".runtime" / "agents" / "default" / ".claude" / "skills"
        )
        assert runtime_skills.is_dir(), "Compiler should produce .claude/skills/"
        runtime_skill_names = [s.name for s in runtime_skills.iterdir()]
        assert len(runtime_skill_names) > 0, "Default role should have at least one skill"
        for name in runtime_skill_names:
            dst = skills_dir / name
            assert dst.is_symlink(), f"{name} should be a symlink in agent workspace"

    # ── 5. settings.local.json deep-merged ──

    def test_assign_settings_deep_merged(self) -> None:
        """verify settings.local.json is deep-merged (hooks present)."""
        result = self._assign("bot-a", "default")
        assert result.exit_code == 0, result.output

        settings_path = self._agent_workspace("bot-a") / ".claude" / "settings.local.json"
        assert settings_path.is_file()
        settings = json.loads(settings_path.read_text())
        # The compiled default role produces hooks in settings.local.json
        runtime_settings_path = (
            self.app_dir / ".runtime" / "agents" / "default" / ".claude" / "settings.local.json"
        )
        assert runtime_settings_path.is_file(), "Compiler should produce settings.local.json"
        runtime_settings = json.loads(runtime_settings_path.read_text())
        # The workspace settings must contain at least the keys from the runtime settings
        for key in runtime_settings:
            assert key in settings, f"Expected key '{key}' in merged settings"
        # Specifically check hooks are present if the runtime has them
        if "hooks" in runtime_settings:
            assert "hooks" in settings
            for hook_name in runtime_settings["hooks"]:
                assert hook_name in settings["hooks"]
        # The workspace was initialized with {"permissions": {"allow": []}} by
        # _get_agent_workspace, so permissions must survive the deep merge
        assert "permissions" in settings

    # ── 6. flow.yaml deep-merged ──

    def test_assign_flow_yaml_deep_merged(self) -> None:
        """verify flow.yaml is deep-merged."""
        result = self._assign("bot-a", "default")
        assert result.exit_code == 0, result.output

        flow_dst = self._agent_workspace("bot-a") / "flow.yaml"
        runtime_flow = self.app_dir / ".runtime" / "agents" / "default" / "flow.yaml"
        assert runtime_flow.is_file(), "Compiler should produce flow.yaml per role"
        assert flow_dst.is_file(), "assign should copy/merge flow.yaml to agent workspace"

        dst_data = yaml.safe_load(flow_dst.read_text())
        src_data = yaml.safe_load(runtime_flow.read_text())
        # All top-level keys from source must be present in destination
        for key in src_data:
            assert key in dst_data, f"Expected key '{key}' in merged flow.yaml"

    # ── 7. commitment.yaml deep-merged ──

    def test_assign_commitment_yaml_deep_merged(self) -> None:
        """verify commitment.yaml is deep-merged.

        The default template has no commitments, so we create one manually in
        the compiled output to exercise the merge path.
        """
        # Write a synthetic commitment.yaml into the runtime role directory
        role_dir = self.app_dir / ".runtime" / "agents" / "default"
        commitment_data = {
            "commitments": {
                "C1": {
                    "from": {"role": "default", "action": "submit"},
                    "to": {"role": "reviewer", "action": "review"},
                    "condition": "within 24h",
                }
            }
        }
        with (role_dir / "commitment.yaml").open("w") as f:
            yaml.dump(commitment_data, f)

        result = self._assign("bot-a", "default")
        assert result.exit_code == 0, result.output

        dst = self._agent_workspace("bot-a") / "commitment.yaml"
        assert dst.is_file()
        dst_data = yaml.safe_load(dst.read_text())
        assert "commitments" in dst_data
        assert "C1" in dst_data["commitments"]

        # Assign again with a second commitment to verify merge (not overwrite)
        commitment_data["commitments"]["C2"] = {
            "from": {"role": "default", "action": "create"},
            "to": {"role": "reviewer", "action": "audit"},
            "condition": "immediately",
        }
        with (role_dir / "commitment.yaml").open("w") as f:
            yaml.dump(commitment_data, f)

        result2 = self._assign("bot-a", "default")
        assert result2.exit_code == 0, result2.output

        dst_data2 = yaml.safe_load(dst.read_text())
        assert "C1" in dst_data2["commitments"]
        assert "C2" in dst_data2["commitments"]


class TestAssignMerge:
    """Lightweight unit tests for the ``assign`` command's merge logic.

    Instead of running ``new`` + ``deploy`` (which depend on templates and the
    compiler), each test builds a minimal fake installed app under ``tmp_path``
    that mimics the directory layout produced by ``install``:

        tmp_path/
        └── ws/                           ← mocked _workspace_root()
            ├── installs.json
            └── dev/
                └── apps/test-app/
                    └── .runtime/agents/{role}/   ← hand-crafted artifacts
    """

    APP_NAME = "test-app"
    CHANNEL = "#dev"
    CHANNEL_NAME = "dev"

    # ── fixtures ──

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    @pytest.fixture
    def ws(self, tmp_path: Path, monkeypatch) -> Path:
        """Create the fake workspace root and wire ``_workspace_root``.

        Returns the workspace root directory (``tmp_path / "ws"``).
        """
        ws_root = tmp_path / "ws"
        ws_root.mkdir()
        monkeypatch.setattr("socialwares.cli._workspace_root", lambda: ws_root)

        # App directory (the "installed" app)
        app_dir = ws_root / self.CHANNEL_NAME / "apps" / self.APP_NAME
        app_dir.mkdir(parents=True)

        # installs.json — consumed by _find_install_by_channel
        installs = [
            {
                "app_name": self.APP_NAME,
                "app_dir": str(app_dir),
                "channel": self.CHANNEL,
                "roles": ["default", "evolver"],
            }
        ]
        (ws_root / "installs.json").write_text(json.dumps(installs, indent=2))
        return ws_root

    # ── helpers ──

    def _app_dir(self, ws: Path) -> Path:
        return ws / self.CHANNEL_NAME / "apps" / self.APP_NAME

    def _role_dir(self, ws: Path, role: str) -> Path:
        return self._app_dir(ws) / ".runtime" / "agents" / role

    def _agent_ws(self, ws: Path, agent: str = "bot-x") -> Path:
        return ws / self.CHANNEL_NAME / "agents" / agent

    def _make_role(
        self,
        ws: Path,
        role: str,
        *,
        soul_md: str | None = None,
        skills: dict[str, str] | None = None,
        settings_json: dict | None = None,
        flow_yaml: dict | None = None,
        commitment_yaml: dict | None = None,
    ) -> Path:
        """Populate ``.runtime/agents/{role}/`` with hand-crafted artifacts."""
        rd = self._role_dir(ws, role)
        rd.mkdir(parents=True, exist_ok=True)

        if soul_md is not None:
            (rd / "SOUL.md").write_text(soul_md, encoding="utf-8")

        if skills is not None:
            skills_dir = rd / ".claude" / "skills"
            skills_dir.mkdir(parents=True, exist_ok=True)
            for name, content in skills.items():
                sd = skills_dir / name
                sd.mkdir(exist_ok=True)
                (sd / "SKILL.md").write_text(content, encoding="utf-8")

        if settings_json is not None:
            claude_dir = rd / ".claude"
            claude_dir.mkdir(parents=True, exist_ok=True)
            (claude_dir / "settings.local.json").write_text(
                json.dumps(settings_json, indent=2)
            )

        if flow_yaml is not None:
            with (rd / "flow.yaml").open("w", encoding="utf-8") as f:
                yaml.dump(flow_yaml, f, default_flow_style=False, allow_unicode=True)

        if commitment_yaml is not None:
            with (rd / "commitment.yaml").open("w", encoding="utf-8") as f:
                yaml.dump(commitment_yaml, f, default_flow_style=False, allow_unicode=True)

        return rd

    def _assign(self, runner: CliRunner, agent: str, role: str) -> object:
        return runner.invoke(
            main,
            ["assign", agent, "--role", role, "--channel", self.CHANNEL],
        )

    # ── 1. SOUL.md — single assign ──

    def test_soul_md_single_assign(self, runner, ws) -> None:
        """Assigning the default role writes SOUL.md with source markers."""
        self._make_role(ws, "default", soul_md="# Default soul\nYou are helpful.")
        result = self._assign(runner, "bot-x", "default")
        assert result.exit_code == 0, result.output

        soul = (self._agent_ws(ws) / "SOUL.md").read_text()
        assert f"<!-- socialware:{self.APP_NAME}:default -->" in soul
        assert f"<!-- /socialware:{self.APP_NAME}:default -->" in soul
        assert "# Default soul" in soul

    # ── 2. SOUL.md — multi-role ──

    def test_soul_md_multi_role(self, runner, ws) -> None:
        """Assigning default then evolver produces two tagged blocks."""
        self._make_role(ws, "default", soul_md="# Default role")
        self._make_role(ws, "evolver", soul_md="# Evolver role")

        r1 = self._assign(runner, "bot-x", "default")
        assert r1.exit_code == 0, r1.output
        r2 = self._assign(runner, "bot-x", "evolver")
        assert r2.exit_code == 0, r2.output

        soul = (self._agent_ws(ws) / "SOUL.md").read_text()
        assert f"<!-- socialware:{self.APP_NAME}:default -->" in soul
        assert f"<!-- /socialware:{self.APP_NAME}:default -->" in soul
        assert f"<!-- socialware:{self.APP_NAME}:evolver -->" in soul
        assert f"<!-- /socialware:{self.APP_NAME}:evolver -->" in soul
        assert "# Default role" in soul
        assert "# Evolver role" in soul

    # ── 3. SOUL.md — idempotency ──

    def test_soul_md_idempotency(self, runner, ws) -> None:
        """Assigning the same role twice keeps exactly one block (no duplication)."""
        self._make_role(ws, "default", soul_md="# Idempotent soul")

        self._assign(runner, "bot-x", "default")
        self._assign(runner, "bot-x", "default")

        soul = (self._agent_ws(ws) / "SOUL.md").read_text()
        marker = f"<!-- socialware:{self.APP_NAME}:default -->"
        assert soul.count(marker) == 1
        assert "# Idempotent soul" in soul

    # ── 4. Skills symlink ──

    def test_skills_symlink(self, runner, ws) -> None:
        """Assigning a role creates correct symlinks under .claude/skills/."""
        self._make_role(
            ws,
            "default",
            soul_md="# soul",
            skills={
                "check_health": "# Check Health",
                "report_status": "# Report Status",
            },
        )

        result = self._assign(runner, "bot-x", "default")
        assert result.exit_code == 0, result.output

        agent_skills = self._agent_ws(ws) / ".claude" / "skills"
        assert agent_skills.is_dir()

        for skill_name in ("check_health", "report_status"):
            link = agent_skills / skill_name
            assert link.is_symlink(), f"{skill_name} should be a symlink"
            resolved = link.resolve()
            assert resolved.is_dir()
            assert (resolved / "SKILL.md").is_file()

    def test_skills_symlink_does_not_overwrite_user_dir(self, runner, ws) -> None:
        """If a non-symlink skill directory already exists, it is not replaced."""
        self._make_role(
            ws,
            "default",
            soul_md="# soul",
            skills={"my_skill": "# Framework version"},
        )

        # Pre-create a real directory as if the user placed it there
        agent_skills = self._agent_ws(ws) / ".claude" / "skills"
        agent_skills.mkdir(parents=True, exist_ok=True)
        user_skill = agent_skills / "my_skill"
        user_skill.mkdir()
        (user_skill / "SKILL.md").write_text("# User version")

        result = self._assign(runner, "bot-x", "default")
        assert result.exit_code == 0, result.output

        # The user's directory should be preserved, not overwritten
        assert not user_skill.is_symlink()
        assert (user_skill / "SKILL.md").read_text() == "# User version"

    # ── 5. settings.local.json merge ──

    def test_settings_json_created(self, runner, ws) -> None:
        """Assigning a role with hooks config writes settings.local.json."""
        hooks_cfg = {
            "hooks": {
                "UserPromptSubmit": [
                    {"hooks": [{"type": "command", "command": "echo hi", "timeout": 5}]}
                ]
            }
        }
        self._make_role(ws, "default", soul_md="# soul", settings_json=hooks_cfg)

        result = self._assign(runner, "bot-x", "default")
        assert result.exit_code == 0, result.output

        settings = json.loads(
            (self._agent_ws(ws) / ".claude" / "settings.local.json").read_text()
        )
        assert "hooks" in settings
        assert "UserPromptSubmit" in settings["hooks"]

    def test_settings_json_deep_merges_with_existing(self, runner, ws) -> None:
        """settings.local.json deep-merges new hooks with pre-existing permissions.

        ``_get_agent_workspace`` initialises the file with
        ``{"permissions": {"allow": []}}`` before ``assign`` merges hooks in.
        """
        hooks_cfg = {
            "hooks": {
                "PreToolUse": [
                    {"hooks": [{"type": "command", "command": "echo check"}]}
                ]
            }
        }
        self._make_role(ws, "default", soul_md="# soul", settings_json=hooks_cfg)

        result = self._assign(runner, "bot-x", "default")
        assert result.exit_code == 0, result.output

        settings = json.loads(
            (self._agent_ws(ws) / ".claude" / "settings.local.json").read_text()
        )
        # Both the original permissions and the new hooks must survive
        assert "permissions" in settings
        assert "hooks" in settings
        assert "PreToolUse" in settings["hooks"]

    # ── 6. flow.yaml deep merge ──

    def test_flow_yaml_first_assign_copies(self, runner, ws) -> None:
        """First assign copies flow.yaml verbatim when no destination file exists."""
        flow_data = {
            "direct_actions": [{"action": "check_health", "role": ["default"]}],
        }
        self._make_role(ws, "default", soul_md="# soul", flow_yaml=flow_data)

        result = self._assign(runner, "bot-x", "default")
        assert result.exit_code == 0, result.output

        dst = self._agent_ws(ws) / "flow.yaml"
        assert dst.is_file()
        data = yaml.safe_load(dst.read_text())
        assert data["direct_actions"][0]["action"] == "check_health"

    def test_flow_yaml_deep_merge_two_roles(self, runner, ws) -> None:
        """Assigning a second role deep-merges flow.yaml (new top-level keys appear)."""
        default_flow = {
            "direct_actions": [{"action": "check_health", "role": ["default"]}],
        }
        evolver_flow = {
            "flows": {
                "review": {
                    "resource": "PR",
                    "states": ["open", "merged"],
                    "transitions": [],
                }
            },
        }
        self._make_role(ws, "default", soul_md="# soul", flow_yaml=default_flow)
        self._make_role(ws, "evolver", soul_md="# soul", flow_yaml=evolver_flow)

        r1 = self._assign(runner, "bot-x", "default")
        assert r1.exit_code == 0, r1.output
        r2 = self._assign(runner, "bot-x", "evolver")
        assert r2.exit_code == 0, r2.output

        data = yaml.safe_load((self._agent_ws(ws) / "flow.yaml").read_text())
        assert "direct_actions" in data, "default role's key must survive"
        assert "flows" in data, "evolver role's key must be merged in"

    # ── 7. commitment.yaml merge ──

    def test_commitment_yaml_first_assign_copies(self, runner, ws) -> None:
        """First assign copies commitment.yaml verbatim."""
        cmt_data = {
            "commitments": {
                "respond": {
                    "from": {"role": "default", "action": "submit"},
                    "to": {"role": "default", "action": "ack"},
                    "condition": "always",
                }
            }
        }
        self._make_role(ws, "default", soul_md="# soul", commitment_yaml=cmt_data)

        result = self._assign(runner, "bot-x", "default")
        assert result.exit_code == 0, result.output

        dst = self._agent_ws(ws) / "commitment.yaml"
        assert dst.is_file()
        data = yaml.safe_load(dst.read_text())
        assert "respond" in data["commitments"]

    def test_commitment_yaml_deep_merge_two_roles(self, runner, ws) -> None:
        """Assigning a second role deep-merges commitment.yaml."""
        default_cmt = {
            "commitments": {
                "respond": {
                    "from": {"role": "default", "action": "submit"},
                    "to": {"role": "default", "action": "ack"},
                    "condition": "always",
                }
            }
        }
        evolver_cmt = {
            "commitments": {
                "evolve_fix": {
                    "from": {"role": "evolver", "action": "inspect"},
                    "to": {"role": "evolver", "action": "fix"},
                    "condition": "on_failure",
                }
            }
        }
        self._make_role(ws, "default", soul_md="# soul", commitment_yaml=default_cmt)
        self._make_role(ws, "evolver", soul_md="# soul", commitment_yaml=evolver_cmt)

        r1 = self._assign(runner, "bot-x", "default")
        assert r1.exit_code == 0, r1.output
        r2 = self._assign(runner, "bot-x", "evolver")
        assert r2.exit_code == 0, r2.output

        data = yaml.safe_load((self._agent_ws(ws) / "commitment.yaml").read_text())
        assert "respond" in data["commitments"], "default commitment must survive"
        assert "evolve_fix" in data["commitments"], "evolver commitment must be merged in"
