"""App declarative API — defines the structure and relationships of a Socialware App.

Usage:
    from socialwares import App

    app = App("task-review")
    app.scope(file="agent/scope/scope.md")
    app.role("default", file="agent/role/default.md")
    app.action("create_task", role=["default"])
    flow = app.flow("task_lifecycle", resource="task")
    flow.states("draft", "submitted")
    flow.transition("draft", "submit", "submitted", role=["default"])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ActionDef:
    """action → role mapping."""

    name: str
    roles: list[str]


@dataclass
class TransitionDef:
    """State machine transition definition."""

    from_state: str
    action: str
    to_state: str
    role: list[str]


@dataclass
class CommitmentDef:
    """Commitment (constraint) definition."""

    name: str
    from_: tuple[str, str]  # (role, action)
    to: tuple[str, str]  # (role, action)
    condition: str
    on_violation: tuple[str, str] | None = None


class Flow:
    """State machine definition. Created via App.flow()."""

    def __init__(self, name: str, resource: str) -> None:
        self.name = name
        self.resource = resource
        self._states: list[str] = []
        self.transitions: list[TransitionDef] = []

    def states(self, *names: str) -> None:
        """Register the list of states."""
        self._states.extend(names)

    def transition(
        self,
        from_state: str,
        action: str,
        to_state: str,
        *,
        role: list[str],
    ) -> None:
        """Add a single state transition."""
        self.transitions.append(
            TransitionDef(
                from_state=from_state,
                action=action,
                to_state=to_state,
                role=role,
            )
        )

    @property
    def state_names(self) -> list[str]:
        return list(self._states)


def _load_content(
    content: str | None,
    file: str | None,
) -> str:
    """Load content from an inline string or a file path."""
    if content is not None and file is not None:
        raise ValueError("Cannot specify both content and file")
    if file is not None:
        return Path(file).read_text(encoding="utf-8")
    if content is not None:
        return content
    raise ValueError("Must specify either content or file")


@dataclass
class RoleDef:
    """Role definition."""

    name: str
    content: str


class App:
    """Declarative definition of a Socialware App.

    An App instance contains the relationship definitions for the four primitives:
    - scope: capability boundary
    - role: role descriptions
    - action: action → role mapping
    - flow: state machine
    - commitment: constraints
    """

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._scope_content: str = ""
        self._roles: dict[str, RoleDef] = {}
        self._actions: dict[str, ActionDef] = {}
        self._flows: list[Flow] = []
        self._commitments: list[CommitmentDef] = []

    # ── Scope ──

    def scope(
        self,
        content: str | None = None,
        *,
        file: str | None = None,
    ) -> None:
        """Define the Scope (capability boundary)."""
        self._scope_content = _load_content(content, file)

    @property
    def scope_content(self) -> str:
        return self._scope_content

    # ── Role ──

    def role(
        self,
        name: str,
        content: str | None = None,
        *,
        file: str | None = None,
    ) -> None:
        """Define a Role (role description)."""
        loaded = _load_content(content, file)
        self._roles[name] = RoleDef(name=name, content=loaded)

    @property
    def roles(self) -> dict[str, RoleDef]:
        return dict(self._roles)

    # ── Action (part of Flow) ──

    def action(self, name: str, *, role: list[str]) -> None:
        """Register an action → role mapping.

        The action name corresponds to the agent/flow/{name}/SKILL.md directory.
        The directory and SKILL.md are validated at compile time.
        """
        self._actions[name] = ActionDef(name=name, roles=list(role))

    @property
    def actions(self) -> dict[str, ActionDef]:
        return dict(self._actions)

    # ── Flow (state machine) ──

    def flow(self, name: str, *, resource: str) -> Flow:
        """Create and register a state machine."""
        f = Flow(name=name, resource=resource)
        self._flows.append(f)
        return f

    @property
    def flows(self) -> list[Flow]:
        return list(self._flows)

    # ── Commitment ──

    def commitment(
        self,
        name: str,
        *,
        from_: tuple[str, str],
        to: tuple[str, str],
        condition: str,
        on_violation: tuple[str, str] | None = None,
    ) -> None:
        """Define a Commitment (constraint)."""
        self._commitments.append(
            CommitmentDef(
                name=name,
                from_=from_,
                to=to,
                condition=condition,
                on_violation=on_violation,
            )
        )

    @property
    def commitments(self) -> list[CommitmentDef]:
        return list(self._commitments)

    # ── Helper methods ──

    def actions_for_role(self, role_name: str) -> list[str]:
        """Return all action names assigned to a given role."""
        result = [a.name for a in self._actions.values() if role_name in a.roles]
        # Also include actions from flow transitions
        for f in self._flows:
            for t in f.transitions:
                if role_name in t.role and t.action not in result:
                    result.append(t.action)
        return result
