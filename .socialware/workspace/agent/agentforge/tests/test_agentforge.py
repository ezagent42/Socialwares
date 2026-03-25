"""Tests for AgentForge workspace configuration."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

WS_ROOT = Path(__file__).parent.parent
AGENT_DIR = WS_ROOT / "agent"


@pytest.fixture
def workspace_copy(tmp_path):
    dest = tmp_path / "agentforge"
    shutil.copytree(WS_ROOT, dest, ignore=shutil.ignore_patterns("node_modules", ".next", "__pycache__", ".runtime"))
    return dest


@pytest.fixture
def deployed(workspace_copy):
    deploy_sh = workspace_copy / "agent" / "deploy.sh"
    result = subprocess.run(
        f'bash "{deploy_sh}"', shell=True,
        capture_output=True, text=True, cwd=str(workspace_copy),
    )
    assert result.returncode == 0, f"deploy failed:\n{result.stderr}\n{result.stdout}"
    return workspace_copy / ".runtime"


class TestRoles:
    EXPECTED_ROLES = ["agentforge", "default", "dev", "reviewer"]

    def test_all_roles_exist(self):
        for role in self.EXPECTED_ROLES:
            assert (AGENT_DIR / "role" / role).is_dir()
            assert (AGENT_DIR / "role" / role / "SOUL.md").exists()

    def test_agentforge_soul_content(self):
        soul = (AGENT_DIR / "role" / "agentforge" / "SOUL.md").read_text(encoding="utf-8")
        assert "AgentForge" in soul

    def test_reviewer_soul_content(self):
        soul = (AGENT_DIR / "role" / "reviewer" / "SOUL.md").read_text(encoding="utf-8")
        assert "review" in soul.lower()

    def test_deploy_creates_all_roles(self, deployed):
        for role in self.EXPECTED_ROLES:
            assert (deployed / "agents" / role).is_dir()
            assert (deployed / "agents" / role / "SOUL.md").exists()


class TestScope:
    def test_scope_exists(self):
        assert (AGENT_DIR / "scope" / "SOUL.md").exists()

    def test_scope_mentions_capabilities(self):
        content = (AGENT_DIR / "scope" / "SOUL.md").read_text(encoding="utf-8")
        assert "role" in content.lower()
        assert "skill" in content.lower()


class TestSkills:
    EXPECTED_SKILLS = [
        "create_role", "create_skill", "edit_primitives",
        "export_bundle", "import_bundle",
        "evaluate", "eval_report", "evolve",
        "review_config", "approve_config", "reject_config",
        "zchat_connect", "check_health", "setup_claude",
    ]

    def test_all_skills_exist(self):
        for skill in self.EXPECTED_SKILLS:
            skill_md = AGENT_DIR / "flow" / skill / "SKILL.md"
            assert skill_md.exists(), f"Missing: {skill}"

    def test_skills_have_frontmatter(self):
        for skill in self.EXPECTED_SKILLS:
            content = (AGENT_DIR / "flow" / skill / "SKILL.md").read_text(encoding="utf-8")
            assert content.startswith("---"), f"{skill} missing frontmatter"
            assert f"name: {skill}" in content, f"{skill} frontmatter missing name"

    def test_create_skill_mentions_three_piece(self):
        content = (AGENT_DIR / "flow" / "create_skill" / "SKILL.md").read_text(encoding="utf-8")
        assert "src/app.py" in content
        assert "flow.yaml" in content


class TestFlowYaml:
    def test_flow_yaml_exists(self):
        assert (AGENT_DIR / "flow" / "flow.yaml").exists()

    def test_flow_yaml_valid(self):
        data = yaml.safe_load((AGENT_DIR / "flow" / "flow.yaml").read_text(encoding="utf-8"))
        assert "direct_actions" in data

    def test_has_agent_review_state_machine(self):
        data = yaml.safe_load((AGENT_DIR / "flow" / "flow.yaml").read_text(encoding="utf-8"))
        assert "flows" in data
        assert "agent_review" in data["flows"]

    def test_all_management_actions_registered(self):
        data = yaml.safe_load((AGENT_DIR / "flow" / "flow.yaml").read_text(encoding="utf-8"))
        actions = {a["action"] for a in data["direct_actions"]}
        expected = {"create_role", "create_skill", "edit_primitives", "export_bundle",
                    "import_bundle", "evaluate", "eval_report", "evolve", "zchat_connect", "check_health"}
        assert expected <= actions, f"Missing: {expected - actions}"

    def test_agentforge_actions_bound_correctly(self):
        data = yaml.safe_load((AGENT_DIR / "flow" / "flow.yaml").read_text(encoding="utf-8"))
        agentforge_actions = {"create_role", "create_skill", "edit_primitives",
                              "export_bundle", "import_bundle", "evaluate", "eval_report", "evolve", "zchat_connect"}
        for action in data["direct_actions"]:
            if action["action"] in agentforge_actions:
                assert "agentforge" in action["role"], f"{action['action']} not bound to agentforge"

    def test_reviewer_actions_bound_correctly(self):
        data = yaml.safe_load((AGENT_DIR / "flow" / "flow.yaml").read_text(encoding="utf-8"))
        reviewer_actions = {"review_config", "approve_config", "reject_config"}
        for action in data["direct_actions"]:
            if action["action"] in reviewer_actions:
                assert "reviewer" in action["role"], f"{action['action']} not bound to reviewer"

    def test_deploy_gives_agentforge_management_skills(self, deployed):
        skills = {s.name for s in (deployed / "agents" / "agentforge" / ".claude" / "skills").iterdir()}
        expected = {"create_role", "create_skill", "edit_primitives", "export_bundle",
                    "import_bundle", "evaluate", "eval_report", "evolve", "zchat_connect", "check_health"}
        assert expected <= skills, f"Missing after deploy: {expected - skills}"

    def test_deploy_gives_reviewer_only_review_skills(self, deployed):
        skills = {s.name for s in (deployed / "agents" / "reviewer" / ".claude" / "skills").iterdir()}
        assert "review_config" in skills
        assert "approve_config" in skills
        assert "reject_config" in skills
        assert "create_role" not in skills  # reviewer shouldn't have this
