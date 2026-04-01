"""编译器测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from socialwares.app import App
from socialwares.compiler import Compiler, CompileResult


def _make_project(tmp_path: Path) -> tuple[App, Path]:
    """创建一个最小的测试项目结构 + App 对象。"""
    # agent/ 目录
    agent = tmp_path / "agent"
    (agent / "role").mkdir(parents=True)
    (agent / "scope").mkdir(parents=True)
    (agent / "flow" / "check_health").mkdir(parents=True)
    (agent / "flow" / "create_task").mkdir(parents=True)
    (agent / "flow" / "review_task").mkdir(parents=True)
    (agent / "flow" / "evolve_structure_check" / "scripts").mkdir(parents=True)
    (agent / "flow" / "evolve_structure_check" / "references").mkdir(parents=True)

    # 内容文件
    (agent / "scope" / "scope.md").write_text("# Scope\nTask management app")
    (agent / "role" / "default.md").write_text("# Default\nYou manage tasks.")
    (agent / "role" / "reviewer.md").write_text("# Reviewer\nYou review tasks.")
    (agent / "role" / "evolver.md").write_text("# Evolver\nYou evolve the app.")
    (agent / "flow" / "check_health" / "SKILL.md").write_text("# Check Health")
    (agent / "flow" / "create_task" / "SKILL.md").write_text("# Create Task")
    (agent / "flow" / "review_task" / "SKILL.md").write_text("# Review Task")
    (agent / "flow" / "evolve_structure_check" / "SKILL.md").write_text("# Structure Check")
    (agent / "flow" / "evolve_structure_check" / "scripts" / "check_structure.py").write_text(
        "# check script"
    )

    # App 对象
    app = App("test-app", description="Test")
    app.scope(file=str(agent / "scope" / "scope.md"))
    app.role("default", file=str(agent / "role" / "default.md"))
    app.role("reviewer", file=str(agent / "role" / "reviewer.md"))
    app.role("evolver", file=str(agent / "role" / "evolver.md"))

    app.action("check_health", role=["default", "reviewer"])
    app.action("create_task", role=["default"])
    app.action("review_task", role=["reviewer"])
    app.action("evolve_structure_check", role=["evolver"])

    flow = app.flow("task_lifecycle", resource="task")
    flow.states("draft", "submitted", "reviewed")
    flow.transition("draft", "submit_task", "submitted", role=["default"])
    flow.transition("submitted", "review_task", "reviewed", role=["reviewer"])

    app.commitment(
        "C1",
        from_=("default", "submit_task"),
        to=("reviewer", "review_task"),
        condition="within 24h",
        on_violation=("reviewer", "remind_review"),
    )

    return app, tmp_path


# 需要 submit_task 的 SKILL.md（flow transition 引用了它）
def _add_submit_task(tmp_path: Path) -> None:
    skill_dir = tmp_path / "agent" / "flow" / "submit_task"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text("# Submit Task")


class TestCompileBasic:
    def test_compile_creates_runtime(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        compiler = Compiler(app, project_dir=project)
        result = compiler.compile()
        assert isinstance(result, CompileResult)
        assert (project / ".runtime").is_dir()

    def test_compile_creates_agent_dirs(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        agents_dir = project / ".runtime" / "agents"
        assert (agents_dir / "default").is_dir()
        assert (agents_dir / "reviewer").is_dir()
        assert (agents_dir / "evolver").is_dir()

    def test_compile_creates_data_dirs(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        data = project / ".runtime" / "data"
        assert (data / "prompts").is_dir()
        assert (data / "sessions").is_dir()
        assert (data / "evolve" / "reports").is_dir()


class TestScopeAndRole:
    def test_soul_merges_scope_and_role(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        soul = (project / ".runtime" / "agents" / "default" / "SOUL.md").read_text()
        assert "# Scope" in soul
        assert "Task management app" in soul
        assert "---" in soul
        assert "# Default" in soul
        assert "You manage tasks." in soul

    def test_soul_injects_workflow(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        soul = (project / ".runtime" / "agents" / "default" / "SOUL.md").read_text()
        assert "## Workflows" in soul
        assert "task_lifecycle" in soul
        assert "submit_task" in soul

    def test_workflow_only_for_involved_roles(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        evolver_soul = (project / ".runtime" / "agents" / "evolver" / "SOUL.md").read_text()
        # evolver 不参与 task_lifecycle flow
        assert "## Workflows" not in evolver_soul


class TestFlowSkills:
    def test_skills_symlinked_per_role(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        default_skills = project / ".runtime" / "agents" / "default" / ".claude" / "skills"
        assert (default_skills / "check_health").is_symlink()
        assert (default_skills / "create_task").is_symlink()
        assert not (default_skills / "review_task").exists()  # not assigned to default
        assert not (default_skills / "evolve_structure_check").exists()

    def test_evolver_has_evolve_skills(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        evolver_skills = project / ".runtime" / "agents" / "evolver" / ".claude" / "skills"
        assert (evolver_skills / "evolve_structure_check").is_symlink()
        assert not (evolver_skills / "create_task").exists()

    def test_symlink_resolves_to_skill_dir(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        link = project / ".runtime" / "agents" / "default" / ".claude" / "skills" / "check_health"
        resolved = link.resolve()
        assert resolved == (project / "agent" / "flow" / "check_health").resolve()


class TestFlowValidation:
    def test_missing_skill_dir_raises(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        # 不创建 submit_task 目录 → 校验应该失败
        with pytest.raises(ValueError, match="submit_task"):
            Compiler(app, project_dir=project).compile()

    def test_missing_skill_md_raises(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        # 创建目录但不创建 SKILL.md
        (project / "agent" / "flow" / "submit_task").mkdir(parents=True)
        with pytest.raises(ValueError, match="SKILL.md"):
            Compiler(app, project_dir=project).compile()


class TestGenerateFlowYaml:
    def test_flow_yaml_generated(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        flow_path = project / ".runtime" / "flow.yaml"
        assert flow_path.is_file()
        data = yaml.safe_load(flow_path.read_text())
        assert "direct_actions" in data

    def test_flow_yaml_separates_direct_and_transitions(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        data = yaml.safe_load((project / ".runtime" / "flow.yaml").read_text())
        direct_names = [a["action"] for a in data["direct_actions"]]
        assert "check_health" in direct_names
        assert "create_task" in direct_names
        # submit_task 和 review_task 在 flow transitions 中，不应在 direct_actions
        assert "submit_task" not in direct_names

    def test_flow_yaml_has_transitions(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        data = yaml.safe_load((project / ".runtime" / "flow.yaml").read_text())
        flow = data["flows"]["task_lifecycle"]
        assert flow["states"] == ["draft", "submitted", "reviewed"]
        transitions = flow["transitions"]
        assert len(transitions) == 2
        assert transitions[0]["action"] == "submit_task"


class TestGenerateCommitment:
    def test_commitment_yaml_generated(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        path = project / ".runtime" / "commitment.yaml"
        assert path.is_file()
        data = yaml.safe_load(path.read_text())
        assert "C1" in data["commitments"]
        assert data["commitments"]["C1"]["condition"] == "within 24h"
        assert data["commitments"]["C1"]["from"]["role"] == "default"


class TestHooks:
    def test_claude_hooks_generated(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project, adapter="claude").compile()
        role_dir = project / ".runtime" / "agents" / "default"
        assert (role_dir / ".claude" / "hooks" / "log_prompt.py").is_file()
        assert (role_dir / ".claude" / "hooks" / "log_tool.py").is_file()
        settings = json.loads(
            (role_dir / ".claude" / "settings.local.json").read_text()
        )
        assert "hooks" in settings
        assert "UserPromptSubmit" in settings["hooks"]
        # Verify generated hook scripts have valid Python syntax
        for hook_name in ("log_prompt.py", "log_tool.py"):
            hook_path = role_dir / ".claude" / "hooks" / hook_name
            source = hook_path.read_text()
            compile(source, str(hook_path), "exec")  # raises SyntaxError if invalid

    def test_hook_writes_by_session_id(self, tmp_path: Path) -> None:
        """Hook script writes to {session_id}.jsonl when session_id present."""
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project, adapter="claude").compile()
        hook = project / ".runtime" / "agents" / "default" / ".claude" / "hooks" / "log_prompt.py"

        import subprocess

        # With session_id → writes to {session_id}.jsonl
        result = subprocess.run(
            ["python", str(hook)],
            input='{"prompt":"test","session_id":"sess-42"}',
            capture_output=True, text=True, cwd=str(project),
        )
        prompts_dir = project / ".runtime" / "data" / "prompts"
        assert (prompts_dir / "sess-42.jsonl").is_file()
        line = json.loads((prompts_dir / "sess-42.jsonl").read_text().strip())
        assert line["session_id"] == "sess-42"
        assert line["content"] == "test"

        # Without session_id → falls back to current.jsonl
        subprocess.run(
            ["python", str(hook)],
            input='{"prompt":"no session"}',
            capture_output=True, text=True, cwd=str(project),
        )
        assert (prompts_dir / "current.jsonl").is_file()
        line = json.loads((prompts_dir / "current.jsonl").read_text().strip())
        assert line["session_id"] == ""

    def test_hook_command_uses_no_project(self, tmp_path: Path) -> None:
        """Hook command in settings.local.json uses uv run --no-project."""
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project, adapter="claude").compile()
        settings = json.loads(
            (project / ".runtime" / "agents" / "default" / ".claude" / "settings.local.json").read_text()
        )
        for hook_type in ("UserPromptSubmit", "PreToolUse"):
            cmd = settings["hooks"][hook_type][0]["hooks"][0]["command"]
            assert "--no-project" in cmd

    def test_codex_hooks_generated(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project, adapter="codex").compile()
        role_dir = project / ".runtime" / "agents" / "default"
        assert (role_dir / ".codex" / "hooks.json").is_file()
        assert (role_dir / ".codex" / "config.toml").is_file()
        # codex prompt file is AGENTS.md, not SOUL.md
        assert (role_dir / "AGENTS.md").is_file()
        assert not (role_dir / "SOUL.md").exists()

    def test_kimi_no_hooks(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project, adapter="kimi").compile()
        role_dir = project / ".runtime" / "agents" / "default"
        # kimi 没有 hooks
        assert not (role_dir / ".claude").exists()
        assert not (role_dir / ".codex").exists()
        # 但有 AGENTS.md
        assert (role_dir / "AGENTS.md").is_file()


class TestManifest:
    def test_manifest_generated(self, tmp_path: Path) -> None:
        app, project = _make_project(tmp_path)
        _add_submit_task(project)
        Compiler(app, project_dir=project).compile()
        path = project / ".runtime" / "compile_manifest.yaml"
        assert path.is_file()
        data = yaml.safe_load(path.read_text())
        assert data["app"] == "test-app"
        assert data["adapter"] == "claude"
        assert "default" in data["roles"]
        assert "evolver" in data["roles"]


class TestLoader:
    def test_load_app_from_file(self, tmp_path: Path) -> None:
        from socialwares.loader import load_app

        sw_file = tmp_path / "socialware.py"
        sw_file.write_text(
            'from socialwares import App\napp = App("loaded-app")\napp.scope("test")\n'
        )
        app = load_app(sw_file)
        assert app.name == "loaded-app"
        assert app.scope_content == "test"

    def test_load_app_missing_file(self, tmp_path: Path) -> None:
        from socialwares.loader import load_app

        with pytest.raises(FileNotFoundError):
            load_app(tmp_path / "nonexistent.py")

    def test_load_app_no_app_object(self, tmp_path: Path) -> None:
        from socialwares.loader import load_app

        sw_file = tmp_path / "socialware.py"
        sw_file.write_text("x = 42\n")
        with pytest.raises(ValueError, match="未找到"):
            load_app(sw_file)
