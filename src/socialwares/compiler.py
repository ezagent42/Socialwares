"""Compiler — four primitives + App declaration → .runtime/

Compiles the App object from socialware.py together with the content files
under agent/ into .runtime/ (one agent directory per role).

Python rewrite of the existing deploy.sh.
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


# ── Adapter configuration ──

@dataclass
class AdapterConfig:
    """Adapter-specific directory/file conventions."""

    skills_subdir: str
    hooks_dir: str  # empty string means hooks are not supported
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


# ── Compile result ──

@dataclass
class CompileResult:
    """Summary of a compilation result."""

    roles: dict[str, int] = field(default_factory=dict)  # role_name → skill_count
    output_dir: str = ""
    adapter: str = ""


# ── Compiler ──

class Compiler:
    """Four-primitives compiler.

    Input:  App object (relationship definitions) + agent/ directory (content files)
    Output: .runtime/ (SOUL.md + skills + hooks for each role)
    """

    def __init__(
        self,
        app: App,
        *,
        project_dir: str | Path = ".",
        agent_dir: str = "agent",
        adapter: str = "claude",
        config: dict | None = None,
    ) -> None:
        self.app = app
        self.project_dir = Path(project_dir).resolve()
        self.agent_dir = self.project_dir / agent_dir
        self.config = config or {}
        # Built-in skills from the framework package
        self._builtin_flow_dir = Path(__file__).parent / "templates" / "agent" / "flow"
        if adapter not in ADAPTERS:
            raise ValueError(f"Unknown adapter: {adapter} (supported: {', '.join(ADAPTERS)})")
        self.adapter = adapter
        self.adapter_config = ADAPTERS[adapter]

    def compile(self, output_dir: str | Path | None = None) -> CompileResult:
        """Main compilation pipeline: four primitives → .runtime/"""
        self.output = Path(output_dir) if output_dir else self.project_dir / ".runtime"
        self.output = self.output.resolve()

        result = CompileResult(output_dir=str(self.output), adapter=self.adapter)

        self._create_data_dirs()
        self._clean_removed_roles()
        self._sync_inline_content()
        self._validate_flow()

        for role_name in self.app.roles:
            skill_count = self._compile_role(role_name)
            result.roles[role_name] = skill_count

        self._generate_flow_yaml()
        self._generate_commitment_yaml()
        self._generate_manifest()

        return result

    # ── 1. Data directories ──

    def _create_data_dirs(self) -> None:
        """Create .runtime/data/ subdirectories."""
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

    # ── 2. Clean up removed roles ──

    def _clean_removed_roles(self) -> None:
        """Remove role directories in .runtime/agents/ that no longer exist."""
        agents_dir = self.output / "agents"
        if not agents_dir.exists():
            return
        for old_dir in agents_dir.iterdir():
            if old_dir.is_dir() and old_dir.name not in self.app.roles:
                shutil.rmtree(old_dir)

    # ── 2b. Inline role → generate files ──

    def _sync_inline_content(self) -> None:
        """Auto-generate corresponding files when four primitives are defined inline.

        Maintains agent/ directory integrity. Skips (does not overwrite) existing files.
        """
        # Scope
        scope_dir = self.agent_dir / "scope"
        scope_dir.mkdir(parents=True, exist_ok=True)
        scope_file = scope_dir / "scope.md"
        if not scope_file.is_file() and self.app.scope_content:
            scope_file.write_text(self.app.scope_content, encoding="utf-8")

        # Role
        role_dir = self.agent_dir / "role"
        role_dir.mkdir(parents=True, exist_ok=True)
        for role_name, role_def in self.app.roles.items():
            role_file = role_dir / f"{role_name}.md"
            if not role_file.is_file():
                role_file.write_text(role_def.content, encoding="utf-8")

    # ── 3. Flow validation ──

    def _validate_flow(self) -> None:
        """Validate that every action has a corresponding SKILL.md (project or framework built-in)."""
        errors: list[str] = []

        all_actions: set[str] = set(self.app.actions.keys())
        for f in self.app.flows:
            for t in f.transitions:
                all_actions.add(t.action)

        for action_name in all_actions:
            skill_dir = self._find_skill_dir(action_name)
            if skill_dir is None:
                errors.append(f"action '{action_name}': skill directory not found")
            elif not (skill_dir / "SKILL.md").is_file():
                errors.append(f"action '{action_name}': SKILL.md not found in {skill_dir}")

        if errors:
            raise ValueError("Flow validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    # ── 4. Compile a single role ──

    def _compile_role(self, role_name: str) -> int:
        """Compile one role: Scope+Role→SOUL.md, Flow→skills symlink + workflow injection, Hooks.

        Returns the skill count.
        """
        cfg = self.adapter_config
        role_dir = self.output / "agents" / role_name
        role_dir.mkdir(parents=True, exist_ok=True)

        # workspace root marker
        (role_dir / ".workspace_root").write_text(str(self.project_dir))

        # Clear old adapter artifacts (idempotent: no stale files after switching adapters)
        for old_prompt in ("SOUL.md", "AGENTS.md"):
            old_file = role_dir / old_prompt
            if old_file.is_file():
                old_file.unlink()
        for old_adapter_dir in (".claude", ".agents", ".codex"):
            old_dir = role_dir / old_adapter_dir
            if old_dir.is_dir():
                shutil.rmtree(old_dir)

        # ── Scope + Role → SOUL.md ──
        soul_content = self._build_soul(role_name)
        (role_dir / cfg.prompt_file).write_text(soul_content, encoding="utf-8")

        # ── Flow → skills symlink ──
        skill_count = self._link_skills(role_name, role_dir)

        # ── Commitment + Flow reference files ──
        # commitment and flow are generated as compile artifacts at the .runtime/ root
        # and also copied to each role directory (needed by evolve scripts)

        # ── Hooks ──
        if cfg.hooks_dir:
            self._generate_hooks(role_name, role_dir)

        return skill_count

    # ── Scope + Role → SOUL.md ──

    def _build_soul(self, role_name: str) -> str:
        """Merge scope + role description + workflow injection → SOUL.md content."""
        parts: list[str] = []

        # Scope
        parts.append(self.app.scope_content)
        parts.append("\n---\n")

        # Role
        role_def = self.app.roles[role_name]
        parts.append(role_def.content)

        # Flow → workflow injection
        workflow_text = self._serialize_workflows(role_name)
        if workflow_text:
            parts.append(workflow_text)

        # Backend configuration injection
        api_port = self.config.get("api_port", 8001)
        parts.append(f"\n---\n\n## Backend\n\nAPI: http://localhost:{api_port}\n")

        return "\n".join(parts)

    def _serialize_workflows(self, role_name: str) -> str:
        """Serialize the state machines defined in the App to Markdown text for injection into SOUL.md."""
        if not self.app.flows:
            return ""

        lines = ["\n---\n", "## Workflows"]
        for flow in self.app.flows:
            # Only inject flows that involve this role
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

    def _find_skill_dir(self, action_name: str) -> Path | None:
        """Find skill directory: project agent/flow/ first, then framework built-in."""
        project_skill = self.agent_dir / "flow" / action_name
        if project_skill.is_dir():
            return project_skill
        builtin_skill = self._builtin_flow_dir / action_name
        if builtin_skill.is_dir():
            return builtin_skill
        return None

    # ── Flow → skills symlink ──

    def _link_skills(self, role_name: str, role_dir: Path) -> int:
        """Symlink the skill directory for each action belonging to this role."""
        cfg = self.adapter_config
        skills_dir = role_dir / cfg.skills_subdir
        skills_dir.mkdir(parents=True, exist_ok=True)

        role_actions = self.app.actions_for_role(role_name)
        skill_count = 0

        for action_name in role_actions:
            source = self._find_skill_dir(action_name)
            if source is None:
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

    # ── Flow → flow.yaml (compile artifact) ──

    def _generate_flow_yaml(self) -> None:
        """Serialize and generate flow.yaml from the App object."""
        # Distinguish between direct actions and actions within flow transitions
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
                    "states": f.state_names,
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

        # Also copy to each role directory (needed by evolve scripts)
        for role_name in self.app.roles:
            dest = self.output / "agents" / role_name / "flow.yaml"
            shutil.copy2(flow_path, dest)

    # ── Commitment → commitment.yaml (compile artifact) ──

    def _generate_commitment_yaml(self) -> None:
        """Serialize and generate commitment.yaml from the App object."""
        if not self.app.commitments:
            return

        data = {
            "commitments": {
                c.name: {
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
            }
        }

        commit_path = self.output / "commitment.yaml"
        with commit_path.open("w", encoding="utf-8") as fh:
            yaml.dump(data, fh, default_flow_style=False, allow_unicode=True)

        for role_name in self.app.roles:
            dest = self.output / "agents" / role_name / "commitment.yaml"
            shutil.copy2(commit_path, dest)

    # ── Hooks generation ──

    def _generate_hooks(self, role_name: str, role_dir: Path) -> None:
        """Generate adapter-specific hook scripts and configuration."""
        cfg = self.adapter_config
        hooks_dir = role_dir / cfg.hooks_dir
        hooks_dir.mkdir(parents=True, exist_ok=True)

        # log_prompt.py
        log_prompt = hooks_dir / "log_prompt.py"
        log_prompt.write_text(self._hook_script("user_prompt"), encoding="utf-8")
        log_prompt.chmod(log_prompt.stat().st_mode | stat.S_IEXEC)

        # log_tool.py
        log_tool = hooks_dir / "log_tool.py"
        log_tool.write_text(self._hook_script("tool_call"), encoding="utf-8")
        log_tool.chmod(log_tool.stat().st_mode | stat.S_IEXEC)

        # Register hooks (adapter-specific format)
        if self.adapter == "claude":
            settings_dir = role_dir / ".claude"
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings = {
                "hooks": {
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": f"uv run --no-project python {log_prompt}", "timeout": 5}]}
                    ],
                    "PreToolUse": [
                        {"hooks": [{"type": "command", "command": f"uv run --no-project python {log_tool}", "timeout": 5}]}
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
                        {"hooks": [{"type": "command", "command": f"uv run --no-project python {log_prompt}", "timeout": 5}]}
                    ],
                    "PreToolUse": [
                        {"hooks": [{"type": "command", "command": f"uv run --no-project python {log_tool}", "timeout": 5}]}
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
        """Generate hook Python script content (cross-platform)."""
        if event_type == "user_prompt":
            extract = (
                "entry = {\n"
                "    'timestamp': datetime.now(timezone.utc).isoformat(),\n"
                "    'type': 'user_prompt',\n"
                "    'role': role,\n"
                "    'content': data.get('prompt', ''),\n"
                "    'session_id': data.get('session_id', ''),\n"
                "}"
            )
        else:
            extract = (
                "entry = {\n"
                "    'timestamp': datetime.now(timezone.utc).isoformat(),\n"
                "    'type': 'tool_call',\n"
                "    'role': role,\n"
                "    'tool': data.get('tool_name', ''),\n"
                "    'input': data.get('tool_input', {}),\n"
                "    'session_id': data.get('session_id', ''),\n"
                "}"
            )

        return f'''#!/usr/bin/env python3
"""Hook — record {event_type} for commitment analysis (cross-platform)."""
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

try:
    data = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)

script_dir = Path(__file__).resolve().parent
workspace_root_file = script_dir.parent.parent / ".workspace_root"
if workspace_root_file.is_file():
    workspace_root = Path(workspace_root_file.read_text().strip())
else:
    workspace_root = script_dir.parent.parent.parent

role = script_dir.parent.parent.name
data_dir = workspace_root / ".runtime" / "data" / "prompts"
data_dir.mkdir(parents=True, exist_ok=True)

{extract}

# Write to session-specific file if session_id available, else current.jsonl
session_id = entry.get("session_id", "")
if session_id:
    log_file = data_dir / f"{{session_id}}.jsonl"
else:
    log_file = data_dir / "current.jsonl"
with open(log_file, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\\n")
'''

    # ── Manifest ──

    def _generate_manifest(self) -> None:
        """Generate compile_manifest.yaml."""
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
