"""Tests for deploy.sh compiling the four primitives into .runtime/.

deploy.sh is workspace-local: it reads agent/ from its own directory
and writes .runtime/ to the parent directory.

Coverage:
- .runtime/ directory structure is correctly generated
- data/ shared directory creation
- per-role agents/ directory creation
- SOUL.md correctly merged (scope + role)
- flow/ skills symlinks correctly point to source directories
- commitment/constraints.yaml correctly copied
- Multiple deploy idempotency
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
AGENT_DIR = REPO_ROOT / "agent"


def _create_test_workspace(tmp_path: Path) -> Path:
    """Create a test workspace by copying the template agent/ directory."""
    workspace = tmp_path / "test-app"
    workspace.mkdir()
    shutil.copytree(AGENT_DIR, workspace / "agent")
    return workspace


def run_deploy(workspace: Path) -> subprocess.CompletedProcess:
    """Execute deploy.sh from within a test workspace."""
    deploy_sh = workspace / "agent" / "deploy.sh"
    return subprocess.run(
        [str(deploy_sh)],
        capture_output=True,
        text=True,
        cwd=str(workspace),
    )


@pytest.fixture
def workspace(tmp_path):
    """Create a test workspace with agent/ copied from template."""
    return _create_test_workspace(tmp_path)


@pytest.fixture
def deployed(workspace):
    """Execute deploy and return the .runtime/ path."""
    result = run_deploy(workspace)
    assert result.returncode == 0, f"deploy.sh failed:\n{result.stderr}\n{result.stdout}"
    return workspace / ".runtime"


# ---------------------------------------------------------------------------
# Directory structure
# ---------------------------------------------------------------------------


class TestDirectoryStructure:
    """Test .runtime/ directory structure."""

    def test_data_dirs_created(self, deployed):
        assert (deployed / "data" / "Files").is_dir()
        assert (deployed / "data" / "Sqlite").is_dir()

    def test_agents_dir_created(self, deployed):
        assert (deployed / "agents").is_dir()

    def test_role_dirs_match_agent_role(self, deployed, workspace):
        """agents/ subdirectories should match agent/role/*.md files."""
        expected_roles = {
            f.stem for f in (workspace / "agent" / "role").iterdir()
            if f.is_file() and f.suffix == ".md" and f.name != "README.md"
        }
        actual_roles = {
            d.name for d in (deployed / "agents").iterdir()
            if d.is_dir()
        }
        assert actual_roles == expected_roles

    def test_each_role_has_claude_dir(self, deployed):
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            assert (role_dir / ".claude").is_dir()
            assert (role_dir / ".claude" / "skills").is_dir()
            assert (role_dir / ".claude" / "hooks").is_dir()


# ---------------------------------------------------------------------------
# SOUL.md merge
# ---------------------------------------------------------------------------


class TestSoulMerge:
    """Test SOUL.md merge: scope/scope.md + role/{name}.md."""

    def test_soul_md_exists_for_each_role(self, deployed):
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            soul = role_dir / "SOUL.md"
            assert soul.exists(), f"Missing SOUL.md for {role_dir.name}"
            assert soul.stat().st_size > 0

    def test_soul_contains_scope_content(self, deployed, workspace):
        """SOUL.md should contain content from scope/scope.md."""
        scope_content = (workspace / "agent" / "scope" / "scope.md").read_text()
        scope_marker = scope_content.strip().split("\n")[0]

        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            soul = (role_dir / "SOUL.md").read_text()
            assert scope_marker in soul

    def test_soul_contains_role_content(self, deployed, workspace):
        """SOUL.md should contain content from role/{name}.md."""
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            role_soul_src = workspace / "agent" / "role" / (role_dir.name + ".md")
            if not role_soul_src.exists():
                continue
            role_content = role_soul_src.read_text().strip().split("\n")[0]
            merged = (role_dir / "SOUL.md").read_text()
            assert role_content in merged


# ---------------------------------------------------------------------------
# Flow skills symlinks
# ---------------------------------------------------------------------------


class TestFlowSymlinks:
    """Test flow/ skills symlinks."""

    def test_skills_are_symlinks(self, deployed):
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            skills_dir = role_dir / ".claude" / "skills"
            for skill in skills_dir.iterdir():
                assert skill.is_symlink(), f"{skill} should be a symlink"

    def test_skills_point_to_agent_flow(self, deployed, workspace):
        """Symlinks should resolve to agent/flow/ directories."""
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            skills_dir = role_dir / ".claude" / "skills"
            for skill_link in skills_dir.iterdir():
                if not skill_link.is_symlink():
                    continue
                expected_source = workspace / "agent" / "flow" / skill_link.name
                assert skill_link.resolve() == expected_source.resolve()

    def test_skills_subset_of_flow_dirs(self, deployed, workspace):
        """Each role's skills should be a subset of agent/flow/ directories.

        With flow.yaml role filtering, not every role gets every skill.
        """
        all_skills = {
            d.name for d in (workspace / "agent" / "flow").iterdir()
            if d.is_dir() and d.name != "__pycache__"
        }
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            actual_skills = {
                s.name for s in (role_dir / ".claude" / "skills").iterdir()
            }
            assert actual_skills <= all_skills, (
                f"Role {role_dir.name} has skills not in flow/: "
                f"{actual_skills - all_skills}"
            )
            assert len(actual_skills) > 0, (
                f"Role {role_dir.name} has no skills"
            )

    def test_skill_content_accessible_via_symlink(self, deployed):
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            for skill_link in (role_dir / ".claude" / "skills").iterdir():
                skill_md = skill_link / "SKILL.md"
                if skill_md.exists():
                    content = skill_md.read_text()
                    assert len(content) > 0


# ---------------------------------------------------------------------------
# Commitment
# ---------------------------------------------------------------------------


class TestCommitment:
    """Test commitment/constraints.yaml copy."""

    def test_eval_yaml_copied_to_each_role(self, deployed, workspace):
        src = workspace / "agent" / "commitment" / "constraints.yaml"
        if not src.exists():
            pytest.skip("No constraints.yaml in agent/commitment/")

        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            dest = role_dir / "constraints.yaml"
            assert dest.exists()

    def test_eval_yaml_content_matches(self, deployed, workspace):
        src = workspace / "agent" / "commitment" / "constraints.yaml"
        if not src.exists():
            pytest.skip("No constraints.yaml")

        src_content = src.read_text()
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            dest_content = (role_dir / "constraints.yaml").read_text()
            assert dest_content == src_content


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Test multiple deploy idempotency."""

    def test_double_deploy(self, workspace):
        r1 = run_deploy(workspace)
        assert r1.returncode == 0
        r2 = run_deploy(workspace)
        assert r2.returncode == 0
        runtime = workspace / ".runtime"
        assert (runtime / "data" / "Files").is_dir()
        assert (runtime / "agents").is_dir()


# ---------------------------------------------------------------------------
# Script basics
# ---------------------------------------------------------------------------


class TestDeployScript:
    """Test deploy.sh script itself."""

    def test_deploy_sh_is_executable(self):
        assert os.access(str(AGENT_DIR / "deploy.sh"), os.X_OK)

    def test_start_sh_is_executable(self):
        assert os.access(str(AGENT_DIR / "start.sh"), os.X_OK)

    def test_deploy_returns_zero(self, workspace):
        result = run_deploy(workspace)
        assert result.returncode == 0

    def test_deploy_output_mentions_roles(self, workspace):
        result = run_deploy(workspace)
        assert "Role:" in result.stdout

    def test_deploy_output_mentions_complete(self, workspace):
        result = run_deploy(workspace)
        assert "Deploy complete" in result.stdout


# ---------------------------------------------------------------------------
# Hooks generated
# ---------------------------------------------------------------------------


class TestHooksGenerated:
    """Test that deploy generates runtime hooks."""

    def test_log_action_hook_exists(self, deployed, workspace):
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            hook = role_dir / ".claude" / "hooks" / "log_action.sh"
            assert hook.exists(), f"Missing log_action.sh for {role_dir.name}"
            assert os.access(str(hook), os.X_OK), f"log_action.sh not executable for {role_dir.name}"

    def test_check_violations_hook_exists(self, deployed, workspace):
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            hook = role_dir / ".claude" / "hooks" / "check_violations.sh"
            assert hook.exists(), f"Missing check_violations.sh for {role_dir.name}"
            assert os.access(str(hook), os.X_OK), f"check_violations.sh not executable for {role_dir.name}"

    def test_constraints_yaml_copied(self, deployed, workspace):
        src = workspace / "agent" / "commitment" / "constraints.yaml"
        if not src.exists():
            pytest.skip("No constraints.yaml")
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            dest = role_dir / "constraints.yaml"
            assert dest.exists(), f"Missing constraints.yaml for {role_dir.name}"
