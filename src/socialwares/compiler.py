"""编译器 — 四原语 + App 声明 → .runtime/

将 socialware.py 中的 App 对象 + agent/ 目录下的内容文件
编译为 .runtime/（每个 role 一个 agent 目录）。

对应现有 deploy.sh 的 Python 重写。
"""

from __future__ import annotations

import json
import os
import shutil
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from socialwares.app import App


# ── 适配器配置 ──

@dataclass
class AdapterConfig:
    """适配器特定的目录/文件约定。"""

    skills_subdir: str
    hooks_dir: str  # 空字符串表示不支持 hooks
    prompt_file: str


ADAPTERS: dict[str, AdapterConfig] = {
    "claude": AdapterConfig(
        skills_subdir=".claude/skills",
        hooks_dir=".claude/hooks",
        prompt_file="SOUL.md",
    ),
    "codex": AdapterConfig(
        skills_subdir=".agents/skills",
        hooks_dir=".codex/hooks",
        prompt_file="AGENTS.md",
    ),
    "kimi": AdapterConfig(
        skills_subdir=".agents/skills",
        hooks_dir="",
        prompt_file="AGENTS.md",
    ),
}


# ── 编译结果 ──

@dataclass
class CompileResult:
    """编译结果摘要。"""

    roles: dict[str, int] = field(default_factory=dict)  # role_name → skill_count
    output_dir: str = ""
    adapter: str = ""


# ── 编译器 ──

class Compiler:
    """四原语编译器。

    输入：App 对象（关系定义）+ agent/ 目录（内容文件）
    输出：.runtime/（每个 role 的 SOUL.md + skills + hooks）
    """

    def __init__(
        self,
        app: App,
        *,
        project_dir: str | Path = ".",
        agent_dir: str = "agent",
        adapter: str = "claude",
    ) -> None:
        self.app = app
        self.project_dir = Path(project_dir).resolve()
        self.agent_dir = self.project_dir / agent_dir
        if adapter not in ADAPTERS:
            raise ValueError(f"Unknown adapter: {adapter} (supported: {', '.join(ADAPTERS)})")
        self.adapter = adapter
        self.adapter_config = ADAPTERS[adapter]

    def compile(self, output_dir: str | Path | None = None) -> CompileResult:
        """主编译流程：四原语 → .runtime/"""
        self.output = Path(output_dir) if output_dir else self.project_dir / ".runtime"
        self.output = self.output.resolve()

        result = CompileResult(output_dir=str(self.output), adapter=self.adapter)

        self._create_data_dirs()
        self._clean_removed_roles()
        self._validate_flow()

        for role_name in self.app.roles:
            skill_count = self._compile_role(role_name)
            result.roles[role_name] = skill_count

        self._generate_flow_yaml()
        self._generate_commitment_yaml()
        self._generate_manifest()

        return result

    # ── 1. 数据目录 ──

    def _create_data_dirs(self) -> None:
        """创建 .runtime/data/ 子目录。"""
        for subdir in [
            "data/Files",
            "data/Sqlite",
            "data/prompts",
            "data/sessions",
            "data/evolve/reports",
            "data/evolve/violations",
            "data/evolve/auto_sessions",
        ]:
            (self.output / subdir).mkdir(parents=True, exist_ok=True)

    # ── 2. 清理已删除的 role ──

    def _clean_removed_roles(self) -> None:
        """删除 .runtime/agents/ 中不再存在的 role 目录。"""
        agents_dir = self.output / "agents"
        if not agents_dir.exists():
            return
        for old_dir in agents_dir.iterdir():
            if old_dir.is_dir() and old_dir.name not in self.app.roles:
                shutil.rmtree(old_dir)

    # ── 3. Flow 校验 ──

    def _validate_flow(self) -> None:
        """校验每个 action 都有对应的 agent/flow/{action}/SKILL.md。"""
        flow_dir = self.agent_dir / "flow"
        errors: list[str] = []

        # 收集所有需要校验的 action（直接注册的 + flow transition 中的）
        all_actions: set[str] = set(self.app.actions.keys())
        for f in self.app.flows:
            for t in f.transitions:
                all_actions.add(t.action)

        for action_name in all_actions:
            skill_dir = flow_dir / action_name
            if not skill_dir.is_dir():
                errors.append(f"action '{action_name}': 目录 {skill_dir} 不存在")
            elif not (skill_dir / "SKILL.md").is_file():
                errors.append(f"action '{action_name}': {skill_dir / 'SKILL.md'} 不存在")

        if errors:
            raise ValueError("Flow 校验失败:\n" + "\n".join(f"  - {e}" for e in errors))

    # ── 4. 编译单个 role ──

    def _compile_role(self, role_name: str) -> int:
        """编译一个 role：Scope+Role→SOUL.md, Flow→skills symlink + workflow 注入, Hooks。

        返回 skill 数量。
        """
        cfg = self.adapter_config
        role_dir = self.output / "agents" / role_name
        role_dir.mkdir(parents=True, exist_ok=True)

        # workspace root marker
        (role_dir / ".workspace_root").write_text(str(self.project_dir))

        # 清除旧的 prompt 文件（幂等：切换适配器后不残留）
        for old_prompt in ("SOUL.md", "AGENTS.md"):
            old_file = role_dir / old_prompt
            if old_file.is_file():
                old_file.unlink()

        # ── Scope + Role → SOUL.md ──
        soul_content = self._build_soul(role_name)
        (role_dir / cfg.prompt_file).write_text(soul_content, encoding="utf-8")

        # ── Flow → skills symlink ──
        skill_count = self._link_skills(role_name, role_dir)

        # ── Commitment + Flow 参考文件 ──
        # commitment 和 flow 作为编译产物生成到 .runtime/ 根，同时复制到每个 role
        # （evolve scripts 需要读取）

        # ── Hooks ──
        if cfg.hooks_dir:
            self._generate_hooks(role_name, role_dir)

        return skill_count

    # ── Scope + Role → SOUL.md ──

    def _build_soul(self, role_name: str) -> str:
        """合并 scope + role 描述 + workflow 注入 → SOUL.md 内容。"""
        parts: list[str] = []

        # Scope
        parts.append(self.app.scope_content)
        parts.append("\n---\n")

        # Role
        role_def = self.app.roles[role_name]
        parts.append(role_def.content)

        # Flow → workflow 注入
        workflow_text = self._serialize_workflows(role_name)
        if workflow_text:
            parts.append(workflow_text)

        return "\n".join(parts)

    def _serialize_workflows(self, role_name: str) -> str:
        """将 App 中定义的状态机序列化为 Markdown 文本，注入到 SOUL.md。"""
        if not self.app.flows:
            return ""

        lines = ["\n---\n", "## Workflows"]
        for flow in self.app.flows:
            # 只注入该 role 参与的 flow
            role_involved = any(role_name in t.role for t in flow.transitions)
            if not role_involved:
                continue

            resource_str = f" (resource: {flow.resource})" if flow.resource else ""
            lines.append(f"### {flow.name}{resource_str}")
            for t in flow.transitions:
                roles = ", ".join(t.role)
                lines.append(f"  {t.from_state} → {t.action} (by {roles}) → {t.to_state}")
            lines.append("")

        if len(lines) <= 2:
            return ""
        return "\n".join(lines)

    # ── Flow → skills symlink ──

    def _link_skills(self, role_name: str, role_dir: Path) -> int:
        """为 role symlink 其 action 对应的 skill 目录。"""
        cfg = self.adapter_config
        skills_dir = role_dir / cfg.skills_subdir
        skills_dir.mkdir(parents=True, exist_ok=True)

        role_actions = self.app.actions_for_role(role_name)
        flow_dir = self.agent_dir / "flow"
        skill_count = 0

        for action_name in role_actions:
            source = flow_dir / action_name
            if not source.is_dir():
                continue

            link = skills_dir / action_name
            if link.is_symlink():
                link.unlink()
            elif link.is_dir():
                shutil.rmtree(link)

            target = os.path.relpath(source, link.parent)
            link.symlink_to(target)
            skill_count += 1

        return skill_count

    # ── Flow → flow.yaml（编译产物）──

    def _generate_flow_yaml(self) -> None:
        """从 App 对象序列化生成 flow.yaml。"""
        # 区分 direct actions 和 flow transitions 中的 actions
        transition_actions: set[str] = set()
        for f in self.app.flows:
            for t in f.transitions:
                transition_actions.add(t.action)

        data: dict = {
            "direct_actions": [
                {"action": a.name, "role": a.roles}
                for a in self.app.actions.values()
                if a.name not in transition_actions
            ],
        }

        if self.app.flows:
            data["flows"] = {}
            for f in self.app.flows:
                data["flows"][f.name] = {
                    "resource": f.resource,
                    "transitions": [
                        {
                            "from": t.from_state,
                            "action": t.action,
                            "to": t.to_state,
                            "role": t.role,
                        }
                        for t in f.transitions
                    ],
                }

        flow_path = self.output / "flow.yaml"
        with flow_path.open("w", encoding="utf-8") as fh:
            yaml.dump(data, fh, default_flow_style=False, allow_unicode=True)

        # 也复制到每个 role 目录（evolve scripts 需要）
        for role_name in self.app.roles:
            dest = self.output / "agents" / role_name / "flow.yaml"
            shutil.copy2(flow_path, dest)

    # ── Commitment → commitment.yaml（编译产物）──

    def _generate_commitment_yaml(self) -> None:
        """从 App 对象序列化生成 commitment.yaml。"""
        if not self.app.commitments:
            return

        data = {
            "commitments": [
                {
                    "id": c.name,
                    "from": {"role": c.from_[0], "action": c.from_[1]},
                    "to": {"role": c.to[0], "action": c.to[1]},
                    "condition": c.condition,
                    **(
                        {"on_violation": {"role": c.on_violation[0], "action": c.on_violation[1]}}
                        if c.on_violation
                        else {}
                    ),
                }
                for c in self.app.commitments
            ]
        }

        commit_path = self.output / "commitment.yaml"
        with commit_path.open("w", encoding="utf-8") as fh:
            yaml.dump(data, fh, default_flow_style=False, allow_unicode=True)

        for role_name in self.app.roles:
            dest = self.output / "agents" / role_name / "commitment.yaml"
            shutil.copy2(commit_path, dest)

    # ── Hooks 生成 ──

    def _generate_hooks(self, role_name: str, role_dir: Path) -> None:
        """生成适配器相关的 hook 脚本和配置。"""
        cfg = self.adapter_config
        hooks_dir = role_dir / cfg.hooks_dir
        hooks_dir.mkdir(parents=True, exist_ok=True)

        # log_prompt.sh
        log_prompt = hooks_dir / "log_prompt.sh"
        log_prompt.write_text(self._hook_script("user_prompt"), encoding="utf-8")
        log_prompt.chmod(log_prompt.stat().st_mode | stat.S_IEXEC)

        # log_tool.sh
        log_tool = hooks_dir / "log_tool.sh"
        log_tool.write_text(self._hook_script("tool_call"), encoding="utf-8")
        log_tool.chmod(log_tool.stat().st_mode | stat.S_IEXEC)

        # 注册 hooks（适配器特定格式）
        if self.adapter == "claude":
            settings_dir = role_dir / ".claude"
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings = {
                "hooks": {
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": str(log_prompt), "timeout": 5}]}
                    ],
                    "PreToolUse": [
                        {"hooks": [{"type": "command", "command": str(log_tool), "timeout": 5}]}
                    ],
                }
            }
            (settings_dir / "settings.local.json").write_text(
                json.dumps(settings, indent=2), encoding="utf-8"
            )

        elif self.adapter == "codex":
            codex_dir = role_dir / ".codex"
            codex_dir.mkdir(parents=True, exist_ok=True)
            hooks = {
                "hooks": {
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": str(log_prompt), "timeout": 5}]}
                    ],
                    "PreToolUse": [
                        {"hooks": [{"type": "command", "command": str(log_tool), "timeout": 5}]}
                    ],
                }
            }
            (codex_dir / "hooks.json").write_text(
                json.dumps(hooks, indent=2), encoding="utf-8"
            )
            (codex_dir / "config.toml").write_text(
                "[features]\ncodex_hooks = true\n", encoding="utf-8"
            )

    def _hook_script(self, event_type: str) -> str:
        """生成 hook bash 脚本内容。"""
        if event_type == "user_prompt":
            extract = """
entry = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'type': 'user_prompt',
    'role': role,
    'content': data.get('prompt', ''),
    'session_id': data.get('session_id', ''),
}"""
        else:
            extract = """
entry = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'type': 'tool_call',
    'role': role,
    'tool': data.get('tool_name', ''),
    'input': data.get('tool_input', {}),
    'session_id': data.get('session_id', ''),
}"""

        return f'''#!/usr/bin/env bash
# Hook — record {event_type} for commitment analysis
set -euo pipefail
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY="python3"; command -v python3 >/dev/null 2>&1 || PY="python"

if [ -f "$(cd "$SCRIPT_DIR" && pwd)/../../.workspace_root" ]; then
    WORKSPACE_ROOT=$(cat "$(cd "$SCRIPT_DIR" && pwd)/../../.workspace_root")
else
    WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
fi
DATA_DIR="$WORKSPACE_ROOT/.runtime/data/prompts"
mkdir -p "$DATA_DIR"

$PY -c "
import json, sys, os
from datetime import datetime, timezone
data = json.loads(sys.stdin.read())
role = os.path.basename(os.path.dirname(os.path.dirname('$SCRIPT_DIR')))
{extract}
log_file = os.path.join('$DATA_DIR', 'current.jsonl')
with open(log_file, 'a') as f:
    f.write(json.dumps(entry, ensure_ascii=False) + '\\n')
" <<< "$INPUT" 2>/dev/null || true
'''

    # ── Manifest ──

    def _generate_manifest(self) -> None:
        """生成 compile_manifest.yaml。"""
        manifest = {
            "app": self.app.name,
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "adapter": self.adapter,
            "roles": {},
        }

        for role_name, role_def in self.app.roles.items():
            role_actions = self.app.actions_for_role(role_name)
            manifest["roles"][role_name] = {
                "skills": role_actions,
                "skill_count": len(role_actions),
            }

        if self.app.commitments:
            manifest["commitments"] = [c.name for c in self.app.commitments]

        if self.app.flows:
            manifest["flows"] = [f.name for f in self.app.flows]

        manifest_path = self.output / "compile_manifest.yaml"
        with manifest_path.open("w", encoding="utf-8") as fh:
            yaml.dump(manifest, fh, default_flow_style=False, allow_unicode=True)
