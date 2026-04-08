"""Tests for the App declarative API."""

from __future__ import annotations

import pytest

from socialwares import App, Flow


class TestAppBasic:
    def test_create(self) -> None:
        app = App("test-app", description="Test")
        assert app.name == "test-app"
        assert app.description == "Test"

    def test_scope_inline(self) -> None:
        app = App("test")
        app.scope("inline scope content")
        assert app.scope_content == "inline scope content"

    def test_scope_file(self, tmp_path) -> None:
        scope_file = tmp_path / "scope.md"
        scope_file.write_text("file scope content", encoding="utf-8")
        app = App("test")
        app.scope(file=str(scope_file))
        assert app.scope_content == "file scope content"

    def test_scope_both_raises(self) -> None:
        app = App("test")
        with pytest.raises(ValueError, match="Cannot specify both"):
            app.scope("inline", file="some/path.md")

    def test_scope_neither_raises(self) -> None:
        app = App("test")
        with pytest.raises(ValueError, match="Must specify either"):
            app.scope()


class TestRole:
    def test_role_inline(self) -> None:
        app = App("test")
        app.role("default", "You are the default agent.")
        assert "default" in app.roles
        assert app.roles["default"].content == "You are the default agent."

    def test_role_file(self, tmp_path) -> None:
        role_file = tmp_path / "reviewer.md"
        role_file.write_text("You are a reviewer.", encoding="utf-8")
        app = App("test")
        app.role("reviewer", file=str(role_file))
        assert app.roles["reviewer"].content == "You are a reviewer."

    def test_multiple_roles(self) -> None:
        app = App("test")
        app.role("default", "Default role")
        app.role("reviewer", "Reviewer role")
        app.role("evolver", "Evolver role")
        assert len(app.roles) == 3


class TestAction:
    def test_action_basic(self) -> None:
        app = App("test")
        app.action("check_health", role=["default", "reviewer"])
        assert "check_health" in app.actions
        assert app.actions["check_health"].roles == ["default", "reviewer"]

    def test_multiple_actions(self) -> None:
        app = App("test")
        app.action("create_task", role=["default"])
        app.action("review_task", role=["reviewer"])
        app.action("evolve_structure_check", role=["evolver"])
        assert len(app.actions) == 3

    def test_actions_for_role(self) -> None:
        app = App("test")
        app.action("check_health", role=["default", "reviewer"])
        app.action("create_task", role=["default"])
        app.action("review_task", role=["reviewer"])
        assert set(app.actions_for_role("default")) == {"check_health", "create_task"}
        assert set(app.actions_for_role("reviewer")) == {"check_health", "review_task"}


class TestFlow:
    def test_flow_basic(self) -> None:
        app = App("test")
        flow = app.flow("task_lifecycle", resource="task")
        assert isinstance(flow, Flow)
        assert len(app.flows) == 1
        assert app.flows[0].name == "task_lifecycle"
        assert app.flows[0].resource == "task"

    def test_states(self) -> None:
        app = App("test")
        flow = app.flow("lifecycle", resource="task")
        flow.states("draft", "submitted", "reviewed", "closed")
        assert flow.state_names == ["draft", "submitted", "reviewed", "closed"]

    def test_transitions(self) -> None:
        app = App("test")
        flow = app.flow("lifecycle", resource="task")
        flow.states("draft", "submitted")
        flow.transition("draft", "submit_task", "submitted", role=["default"])
        assert len(flow.transitions) == 1
        t = flow.transitions[0]
        assert t.from_state == "draft"
        assert t.action == "submit_task"
        assert t.to_state == "submitted"
        assert t.role == ["default"]

    def test_flow_actions_included_in_actions_for_role(self) -> None:
        app = App("test")
        app.action("check_health", role=["default"])
        flow = app.flow("lifecycle", resource="task")
        flow.transition("draft", "submit_task", "submitted", role=["default"])
        # submit_task comes from flow transition, should appear in actions_for_role
        role_actions = app.actions_for_role("default")
        assert "check_health" in role_actions
        assert "submit_task" in role_actions


class TestCommitment:
    def test_commitment_basic(self) -> None:
        app = App("test")
        app.commitment(
            "C1",
            from_=("default", "submit_task"),
            to=("reviewer", "review_task"),
            condition="within 24h",
        )
        assert len(app.commitments) == 1
        c = app.commitments[0]
        assert c.name == "C1"
        assert c.from_ == ("default", "submit_task")
        assert c.to == ("reviewer", "review_task")
        assert c.condition == "within 24h"
        assert c.on_violation is None

    def test_commitment_with_violation(self) -> None:
        app = App("test")
        app.commitment(
            "C1",
            from_=("default", "submit_task"),
            to=("reviewer", "review_task"),
            condition="within 24h",
            on_violation=("reviewer", "remind_review"),
        )
        assert app.commitments[0].on_violation == ("reviewer", "remind_review")


class TestFullApp:
    """Full App declaration test, simulating socialware.py usage."""

    def test_full_declaration(self, tmp_path) -> None:
        # Prepare files
        (tmp_path / "scope.md").write_text("Task management scope")
        (tmp_path / "default.md").write_text("Default agent role")
        (tmp_path / "reviewer.md").write_text("Reviewer role")
        (tmp_path / "evolver.md").write_text("Evolver role")

        app = App("task-review", description="Task review workflow")

        app.scope(file=str(tmp_path / "scope.md"))
        app.role("default", file=str(tmp_path / "default.md"))
        app.role("reviewer", file=str(tmp_path / "reviewer.md"))
        app.role("evolver", file=str(tmp_path / "evolver.md"))

        app.action("check_health", role=["default", "reviewer"])
        app.action("create_task", role=["default"])
        app.action("review_task", role=["reviewer"])
        app.action("evolve_structure_check", role=["evolver"])
        app.action("evolve_improve", role=["evolver"])

        flow = app.flow("task_lifecycle", resource="task")
        flow.states("draft", "submitted", "reviewed", "closed")
        flow.transition("draft", "submit_task", "submitted", role=["default"])
        flow.transition("submitted", "review_task", "reviewed", role=["reviewer"])
        flow.transition("reviewed", "close_task", "closed", role=["default"])

        app.commitment(
            "C1",
            from_=("default", "submit_task"),
            to=("reviewer", "review_task"),
            condition="within 24h",
            on_violation=("reviewer", "remind_review"),
        )

        # Verify
        assert app.scope_content == "Task management scope"
        assert len(app.roles) == 3
        assert len(app.actions) == 5
        assert len(app.flows) == 1
        assert len(app.commitments) == 1

        # default role actions: check_health, create_task + submit_task, close_task from flow
        default_actions = app.actions_for_role("default")
        assert "check_health" in default_actions
        assert "create_task" in default_actions
        assert "submit_task" in default_actions
        assert "close_task" in default_actions

        # evolver role actions
        evolver_actions = app.actions_for_role("evolver")
        assert "evolve_structure_check" in evolver_actions
        assert "evolve_improve" in evolver_actions
