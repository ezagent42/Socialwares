"""App 声明式 API — 定义 Socialware App 的结构和关系。

用法:
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
    """action → role 映射。"""

    name: str
    roles: list[str]


@dataclass
class TransitionDef:
    """状态机转移定义。"""

    from_state: str
    action: str
    to_state: str
    role: list[str]


@dataclass
class CommitmentDef:
    """约束定义。"""

    name: str
    from_: tuple[str, str]  # (role, action)
    to: tuple[str, str]  # (role, action)
    condition: str
    on_violation: tuple[str, str] | None = None


class Flow:
    """状态机定义。通过 App.flow() 创建。"""

    def __init__(self, name: str, resource: str) -> None:
        self.name = name
        self.resource = resource
        self._states: list[str] = []
        self.transitions: list[TransitionDef] = []

    def states(self, *names: str) -> None:
        """注册状态列表。"""
        self._states.extend(names)

    def transition(
        self,
        from_state: str,
        action: str,
        to_state: str,
        *,
        role: list[str],
    ) -> None:
        """添加一条状态转移。"""
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
    """从 inline string 或文件路径加载内容。"""
    if content is not None and file is not None:
        raise ValueError("不能同时指定 content 和 file")
    if file is not None:
        return Path(file).read_text(encoding="utf-8")
    if content is not None:
        return content
    raise ValueError("必须指定 content 或 file")


@dataclass
class RoleDef:
    """角色定义。"""

    name: str
    content: str


class App:
    """Socialware App 声明式定义。

    一个 App 实例包含四原语的关系定义:
    - scope: 能力边界
    - role: 角色描述
    - action: action → role 映射
    - flow: 状态机
    - commitment: 约束
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
        """定义 Scope（能力边界）。"""
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
        """定义 Role（角色描述）。"""
        loaded = _load_content(content, file)
        self._roles[name] = RoleDef(name=name, content=loaded)

    @property
    def roles(self) -> dict[str, RoleDef]:
        return dict(self._roles)

    # ── Action（Flow 的一部分）──

    def action(self, name: str, *, role: list[str]) -> None:
        """注册 action → role 映射。

        action 名对应 agent/flow/{name}/SKILL.md 目录。
        编译时校验目录和 SKILL.md 是否存在。
        """
        self._actions[name] = ActionDef(name=name, roles=list(role))

    @property
    def actions(self) -> dict[str, ActionDef]:
        return dict(self._actions)

    # ── Flow（状态机）──

    def flow(self, name: str, *, resource: str) -> Flow:
        """创建并注册一个状态机。"""
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
        """定义 Commitment（约束）。"""
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

    # ── 辅助方法 ──

    def actions_for_role(self, role_name: str) -> list[str]:
        """返回分配给某个 role 的所有 action 名。"""
        result = [a.name for a in self._actions.values() if role_name in a.roles]
        # 也包括 flow transition 中的 action
        for f in self._flows:
            for t in f.transitions:
                if role_name in t.role and t.action not in result:
                    result.append(t.action)
        return result
