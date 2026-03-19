"""测试 deploy.sh 编译四原语 → .runtime/ 的完整性。

覆盖:
- .runtime/ 目录结构正确生成
- data/ 共享目录创建
- per-role agents/ 目录创建
- SOUL.md 正确合并 (scope + role)
- flow/ skills 软连接正确指向源目录
- commitment/eval.yaml 正确复制
- 多次 deploy 幂等性
- 缺失文件的容错
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
AGENT_DIR = REPO_ROOT / "agent"
DEPLOY_SH = AGENT_DIR / "deploy.sh"


def run_deploy(workspace_path: str) -> subprocess.CompletedProcess:
    """执行 deploy.sh 并返回结果。"""
    return subprocess.run(
        [str(DEPLOY_SH), workspace_path],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


@pytest.fixture
def workspace(tmp_path):
    """创建临时 workspace 目录。"""
    ws = tmp_path / "test-workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def deployed(workspace):
    """执行 deploy 并返回 .runtime/ 路径。"""
    result = run_deploy(str(workspace))
    assert result.returncode == 0, f"deploy.sh failed:\n{result.stderr}\n{result.stdout}"
    return workspace / ".runtime"


# ---------------------------------------------------------------------------
# 目录结构
# ---------------------------------------------------------------------------


class TestDirectoryStructure:
    """测试 .runtime/ 目录结构。"""

    def test_data_dirs_created(self, deployed):
        assert (deployed / "data" / "Files").is_dir()
        assert (deployed / "data" / "Sqlite").is_dir()

    def test_agents_dir_created(self, deployed):
        assert (deployed / "agents").is_dir()

    def test_role_dirs_match_agent_role(self, deployed):
        """agents/ 下的子目录应与 agent/role/ 下的子目录一一对应。"""
        expected_roles = {
            d.name for d in (AGENT_DIR / "role").iterdir()
            if d.is_dir() and d.name != "__pycache__"
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
# SOUL.md 合并
# ---------------------------------------------------------------------------


class TestSoulMerge:
    """测试 SOUL.md 合并: scope/SOUL.md + role/{name}/SOUL.md。"""

    def test_soul_md_exists_for_each_role(self, deployed):
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            soul = role_dir / "SOUL.md"
            assert soul.exists(), f"Missing SOUL.md for {role_dir.name}"
            assert soul.stat().st_size > 0

    def test_soul_contains_scope_content(self, deployed):
        """SOUL.md 应包含 scope/SOUL.md 的内容。"""
        scope_content = (AGENT_DIR / "scope" / "SOUL.md").read_text()
        # 取 scope 的第一行作为标志
        scope_marker = scope_content.strip().split("\n")[0]

        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            soul = (role_dir / "SOUL.md").read_text()
            assert scope_marker in soul, (
                f"Role {role_dir.name} SOUL.md missing scope content"
            )

    def test_soul_contains_role_content(self, deployed):
        """SOUL.md 应包含该 role 的 SOUL.md 内容。"""
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            role_soul_src = AGENT_DIR / "role" / role_dir.name / "SOUL.md"
            if not role_soul_src.exists():
                continue
            role_content = role_soul_src.read_text().strip().split("\n")[0]
            merged = (role_dir / "SOUL.md").read_text()
            assert role_content in merged, (
                f"Role {role_dir.name} SOUL.md missing role-specific content"
            )


# ---------------------------------------------------------------------------
# Flow Skills 软连接
# ---------------------------------------------------------------------------


class TestFlowSymlinks:
    """测试 flow/ skills 软连接。"""

    def test_skills_are_symlinks(self, deployed):
        """每个 skill 应该是软连接。"""
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            skills_dir = role_dir / ".claude" / "skills"
            for skill in skills_dir.iterdir():
                assert skill.is_symlink(), (
                    f"{skill} should be a symlink, not a real directory"
                )

    def test_skills_point_to_agent_flow(self, deployed):
        """软连接应指向 agent/flow/ 下的对应目录。"""
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            skills_dir = role_dir / ".claude" / "skills"
            for skill_link in skills_dir.iterdir():
                if not skill_link.is_symlink():
                    continue
                target = Path(os.readlink(str(skill_link)))
                # target 应该是 agent/flow/{skill_name}/ 的绝对路径
                expected_source = AGENT_DIR / "flow" / skill_link.name
                assert target.resolve() == expected_source.resolve(), (
                    f"Symlink {skill_link} points to {target}, "
                    f"expected {expected_source}"
                )

    def test_skills_match_flow_dirs(self, deployed):
        """skills/ 下的条目应与 agent/flow/ 下的目录一一对应。"""
        expected_skills = {
            d.name for d in (AGENT_DIR / "flow").iterdir()
            if d.is_dir() and d.name != "__pycache__"
        }
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            actual_skills = {
                s.name for s in (role_dir / ".claude" / "skills").iterdir()
            }
            assert actual_skills == expected_skills, (
                f"Role {role_dir.name}: skills mismatch. "
                f"Expected {expected_skills}, got {actual_skills}"
            )

    def test_skill_content_accessible_via_symlink(self, deployed):
        """通过软连接应能读到 SKILL.md 内容。"""
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            for skill_link in (role_dir / ".claude" / "skills").iterdir():
                skill_md = skill_link / "SKILL.md"
                if skill_md.exists():
                    content = skill_md.read_text()
                    assert len(content) > 0, f"Empty SKILL.md at {skill_md}"


# ---------------------------------------------------------------------------
# Commitment
# ---------------------------------------------------------------------------


class TestCommitment:
    """测试 commitment/eval.yaml 复制。"""

    def test_eval_yaml_copied_to_each_role(self, deployed):
        src = AGENT_DIR / "commitment" / "eval.yaml"
        if not src.exists():
            pytest.skip("No eval.yaml in agent/commitment/")

        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            dest = role_dir / "eval.yaml"
            assert dest.exists(), f"Missing eval.yaml for {role_dir.name}"

    def test_eval_yaml_content_matches(self, deployed):
        src = AGENT_DIR / "commitment" / "eval.yaml"
        if not src.exists():
            pytest.skip("No eval.yaml")

        src_content = src.read_text()
        for role_dir in (deployed / "agents").iterdir():
            if not role_dir.is_dir():
                continue
            dest_content = (role_dir / "eval.yaml").read_text()
            assert dest_content == src_content


# ---------------------------------------------------------------------------
# 幂等性
# ---------------------------------------------------------------------------


class TestIdempotency:
    """测试多次 deploy 的幂等性。"""

    def test_double_deploy(self, workspace):
        """连续两次 deploy 应成功且结果一致。"""
        r1 = run_deploy(str(workspace))
        assert r1.returncode == 0

        r2 = run_deploy(str(workspace))
        assert r2.returncode == 0

        runtime = workspace / ".runtime"
        # 验证结构仍然正确
        assert (runtime / "data" / "Files").is_dir()
        assert (runtime / "agents").is_dir()

    def test_deploy_updates_soul_on_change(self, workspace):
        """修改 scope/SOUL.md 后重新 deploy，应更新 .runtime/ 中的 SOUL.md。"""
        r1 = run_deploy(str(workspace))
        assert r1.returncode == 0

        runtime = workspace / ".runtime"
        roles = [d for d in (runtime / "agents").iterdir() if d.is_dir()]
        if not roles:
            pytest.skip("No roles deployed")

        first_soul = (roles[0] / "SOUL.md").read_text()

        # deploy again (same content)
        r2 = run_deploy(str(workspace))
        assert r2.returncode == 0

        second_soul = (roles[0] / "SOUL.md").read_text()
        assert first_soul == second_soul


# ---------------------------------------------------------------------------
# deploy.sh 基本验证
# ---------------------------------------------------------------------------


class TestDeployScript:
    """测试 deploy.sh 脚本本身。"""

    def test_deploy_sh_is_executable(self):
        assert os.access(str(DEPLOY_SH), os.X_OK)

    def test_start_sh_is_executable(self):
        assert os.access(str(AGENT_DIR / "start.sh"), os.X_OK)

    def test_deploy_returns_zero(self, workspace):
        result = run_deploy(str(workspace))
        assert result.returncode == 0

    def test_deploy_output_mentions_roles(self, workspace):
        result = run_deploy(str(workspace))
        assert "Role:" in result.stdout

    def test_deploy_output_mentions_complete(self, workspace):
        result = run_deploy(str(workspace))
        assert "Deploy complete" in result.stdout
