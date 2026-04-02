"""CLI — socialwares new / deploy / start / install / assign / uninstall."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml

import click


def _workspace_root() -> Path:
    """Return the .socialware/workspace/ directory."""
    return Path.cwd() / ".socialware" / "workspace"


def _channel_dir(channel: str) -> Path:
    """Return the channel directory. Strips the # prefix."""
    name = channel.lstrip("#")
    return _workspace_root() / name


def _load_config(project_dir: Path) -> dict:
    """Read [tool.socialwares] configuration from pyproject.toml."""
    toml_path = project_dir / "pyproject.toml"
    if not toml_path.is_file():
        return {}
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]
    with toml_path.open("rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get("socialwares", {})


@click.group()
def main() -> None:
    """Socialwares — framework for building Socialware Apps."""


# ── socialwares new ──

def _new_from_source(name: str, source: str) -> None:
    """Create project by cloning from git URL or copying from local path."""
    target = Path(name)
    if target.exists():
        click.echo(f"Error: {name}/ already exists")
        raise SystemExit(1)

    # Clone or copy
    if source.endswith(".git") or source.startswith("git@") or source.startswith("git+"):
        subprocess.run(["git", "clone", source, name], check=True)
    else:
        src_path = Path(source)
        if not src_path.is_dir():
            click.echo(f"Error: {source} is not a directory")
            raise SystemExit(1)
        shutil.copytree(src_path, target, symlinks=True, ignore=shutil.ignore_patterns(
            ".runtime", "__pycache__", ".git", "*.pyc",
        ))

    # Remove .git/ from cloned repo (start fresh)
    git_dir = target / ".git"
    if git_dir.is_dir():
        shutil.rmtree(git_dir)

    # Remove stale symlinks in agent/flow/ (broken built-in skill symlinks)
    flow_dir = target / "agent" / "flow"
    if flow_dir.is_dir():
        for item in flow_dir.iterdir():
            if item.is_symlink():
                item.unlink()

    # Detect old app name from socialware.py
    sw_file = target / "socialware.py"
    if sw_file.is_file():
        content = sw_file.read_text(encoding="utf-8")
        # Replace App("old-name") with App("new-name")
        content = re.sub(r'App\(["\']([^"\']+)["\']\)', f'App("{name}")', content)
        sw_file.write_text(content, encoding="utf-8")

    # Update pyproject.toml name
    toml_file = target / "pyproject.toml"
    if toml_file.is_file():
        content = toml_file.read_text(encoding="utf-8")
        content = re.sub(r'^name\s*=\s*"[^"]*"', f'name = "{name}"', content, flags=re.MULTILINE)
        toml_file.write_text(content, encoding="utf-8")

    click.echo(f"Created {name}/ from {source}")


@main.command()
@click.argument("name")
@click.option("--from", "source", default=None, help="Git URL or local path to clone from")
def new(name: str, source: str | None) -> None:
    """Create a new project."""
    if source:
        _new_from_source(name, source)
        return

    target = Path.cwd() / name
    if target.exists():
        click.echo(f"Error: {target} already exists.")
        raise SystemExit(1)

    import socialwares
    pkg_dir = Path(socialwares.__file__).parent
    templates_dir = pkg_dir / "templates"

    if not templates_dir.is_dir():
        click.echo(f"Error: templates not found at {templates_dir}")
        raise SystemExit(1)

    # Built-in skills managed by the framework — not copied to project
    BUILTIN_SKILLS = {
        "dev_define", "dev_build", "dev_release",
        "evolve_structure_check", "evolve_api_check",
        "evolve_session_diagnose", "evolve_improve", "evolve_auto",
        "inspect", "setup_claude",
    }

    def _ignore_builtin_skills(directory: str, contents: list[str]) -> list[str]:
        """Skip built-in skills when copying templates."""
        if Path(directory).name == "flow" and "SKILL.md" not in contents:
            return [c for c in contents if c in BUILTIN_SKILLS]
        return []

    shutil.copytree(templates_dir, target, ignore=_ignore_builtin_skills)

    # Render placeholders
    for fname in ("socialware.py", "pyproject.toml"):
        fpath = target / fname
        if fpath.is_file():
            content = fpath.read_text()
            content = content.replace("{{APP_NAME}}", name)
            fpath.write_text(content)

    click.echo(f"✓ Created {name}/")
    click.echo(f"  cd {name}")
    click.echo(f"  socialwares deploy")
    click.echo(f"  socialwares start --role default")


# ── socialwares deploy ──

@main.command()
@click.option("--adapter", default=None, help="LLM adapter (claude/codex/kimi)")
def deploy(adapter: str | None) -> None:
    """Compile four primitives to .runtime/"""
    project_dir = Path.cwd()
    config = _load_config(project_dir)
    adapter = adapter or config.get("adapter", "claude")

    from socialwares.loader import load_app
    from socialwares.compiler import Compiler

    sw_path = project_dir / "socialware.py"
    if not sw_path.is_file():
        click.echo("Error: socialware.py not found in current directory.")
        raise SystemExit(1)

    app = load_app(sw_path)
    compiler = Compiler(
        app,
        project_dir=project_dir,
        agent_dir=config.get("agent_dir", "agent"),
        adapter=adapter,
        config=config,
    )
    result = compiler.compile()

    click.echo(f"✓ Compiled {app.name} (adapter: {result.adapter})")
    for role_name, skill_count in result.roles.items():
        click.echo(f"  {role_name}: {skill_count} skills")
    click.echo(f"  Output: {result.output_dir}")


# ── socialwares eject ──

@main.command()
@click.argument("skill_name")
def eject(skill_name: str) -> None:
    """Copy a built-in skill to agent/flow/ for customization."""
    builtin_dir = Path(__file__).parent / "templates" / "agent" / "flow" / skill_name
    if not builtin_dir.is_dir():
        click.echo(f"Error: '{skill_name}' is not a built-in skill")
        raise SystemExit(1)

    config = _load_config(Path.cwd())
    agent_dir = Path(config.get("agent_dir", "agent"))
    target = agent_dir / "flow" / skill_name

    if target.exists() and not target.is_symlink():
        click.echo(f"Error: {target} already exists (not a symlink). Remove it first to re-eject.")
        raise SystemExit(1)

    if target.is_symlink():
        target.unlink()

    shutil.copytree(builtin_dir, target)
    click.echo(f"Ejected '{skill_name}' to {target}/")
    click.echo(f"You can now customize it. Run 'socialwares deploy' to apply changes.")


# ── socialwares start ──

@main.command()
@click.option("--role", required=True, help="Role name (comma-separated for multi)")
@click.option("--adapter", default=None, help="LLM adapter")
@click.option("--prompt", default=None, help="Prompt for SDK mode")
@click.option("--run-all", is_flag=True, help="Run all evolve checks (CI mode)")
def start(role: str, adapter: str | None, prompt: str | None, run_all: bool) -> None:
    """Start an agent (local development)."""
    project_dir = Path.cwd()
    config = _load_config(project_dir)
    adapter = adapter or config.get("adapter", "claude")

    from socialwares.runner import Runner
    runner = Runner(project_dir=project_dir, adapter=adapter)

    roles = [r.strip() for r in role.split(",")]

    if prompt:
        runner.run_sdk(roles[0], prompt)
    elif run_all:
        runner.run_sdk(roles[0], "run all checks and report")
    elif len(roles) == 1:
        runner.start(roles[0])
    else:
        runner.start_multi(roles)


# ── socialwares install ──

@main.command()
@click.argument("source")
@click.option("--channel", required=True, help="IRC channel to install to")
@click.option("--path", "install_path", default=None, help="Override install directory")
def install(source: str, channel: str, install_path: str | None) -> None:
    """Install an App to an IRC channel (git clone + deploy)."""
    app_name = source.rstrip("/").split("/")[-1]
    if app_name.endswith(".git"):
        app_name = app_name[:-4]

    # Install to .socialware/workspace/{channel}/apps/{app}/
    if install_path:
        app_dir = Path(install_path)
    else:
        app_dir = _channel_dir(channel) / "apps" / app_name

    if app_dir.exists():
        # Directory exists but not recorded in installs.json — stale, clean up and reinstall
        if _find_install_by_channel(channel) is None:
            click.echo(f"Cleaning up stale directory {app_dir}...")
            shutil.rmtree(app_dir)
        else:
            click.echo(f"App {app_name} already installed at {app_dir}")
            click.echo(f"Use 'socialwares uninstall {app_name} --channel {channel}' first.")
            raise SystemExit(1)

    click.echo(f"Cloning {source}...")
    app_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", source, str(app_dir)], check=True)

    # deploy
    config = _load_config(app_dir)
    adapter = config.get("adapter", "claude")

    from socialwares.loader import load_app
    from socialwares.compiler import Compiler

    sw_path = app_dir / "socialware.py"
    if not sw_path.is_file():
        click.echo(f"Error: {sw_path} not found in cloned repo.")
        raise SystemExit(1)

    app = load_app(sw_path)
    compiler = Compiler(
        app,
        project_dir=app_dir,
        agent_dir=config.get("agent_dir", "agent"),
        adapter=adapter,
        config=config,
    )
    result = compiler.compile()

    _save_install_info(app_name, app_dir, channel, list(result.roles.keys()))

    click.echo(f"✓ Installed {app_name} to {channel}")
    click.echo(f"  Path: {app_dir}")
    click.echo(f"  Roles: {', '.join(result.roles.keys())}")
    click.echo(f"  Now assign roles: socialwares assign <agent> --role <role> --channel {channel}")


# ── socialwares assign ──

@main.command()
@click.argument("agent_name")
@click.option("--role", required=True, help="Role to assign")
@click.option("--channel", required=True, help="IRC channel")
@click.option("--agent-path", default=None, help="Override agent workspace directory")
def assign(agent_name: str, role: str, channel: str, agent_path: str | None) -> None:
    """Assign a role to an agent in an IRC channel."""
    # Find the app
    info = _find_install_by_channel(channel)
    if info is None:
        click.echo(f"Error: no app installed to channel {channel}")
        raise SystemExit(1)

    app_dir = Path(info["app_dir"])
    runtime_dir = app_dir / ".runtime"
    role_dir = runtime_dir / "agents" / role

    if not role_dir.is_dir():
        available = [p.name for p in (runtime_dir / "agents").iterdir() if p.is_dir()]
        click.echo(f"Error: role '{role}' not found. Available: {', '.join(available)}")
        raise SystemExit(1)

    # Agent workspace path
    if agent_path:
        workspace = Path(agent_path)
        workspace.mkdir(parents=True, exist_ok=True)
    else:
        workspace = _get_agent_workspace(agent_name, channel)

    app_name = info["app_name"]
    source_tag = f"socialware:{app_name}:{role}"

    # ── SOUL.md / AGENTS.md: merge with source markers (idempotent) ──
    for prompt_file in ("SOUL.md", "AGENTS.md"):
        src = role_dir / prompt_file
        if not src.is_file():
            continue
        dst = workspace / prompt_file
        new_block = src.read_text(encoding="utf-8")
        marker_start = f"<!-- {source_tag} -->"
        marker_end = f"<!-- /{source_tag} -->"
        tagged_block = f"{marker_start}\n{new_block}\n{marker_end}"

        if dst.is_file():
            existing = dst.read_text(encoding="utf-8")
            if marker_start in existing:
                # Replace existing block (idempotent)
                pattern = re.escape(marker_start) + r".*?" + re.escape(marker_end)
                existing = re.sub(pattern, tagged_block, existing, flags=re.DOTALL)
            else:
                # Append new block
                existing = existing.rstrip() + "\n\n" + tagged_block + "\n"
            dst.write_text(existing, encoding="utf-8")
        else:
            dst.write_text(tagged_block + "\n", encoding="utf-8")

    # ── Skills: per-skill symlink (append, don't replace) ──
    src_skills = role_dir / ".claude" / "skills"
    if src_skills.is_dir():
        dst_skills = workspace / ".claude" / "skills"
        dst_skills.mkdir(parents=True, exist_ok=True)
        for skill_link in src_skills.iterdir():
            dst_link = dst_skills / skill_link.name
            if dst_link.is_symlink():
                dst_link.unlink()
            elif dst_link.exists():
                continue  # User's own skill — don't override
            target = os.path.relpath(skill_link.resolve(), dst_link.parent)
            dst_link.symlink_to(target)

    # ── settings.local.json: deep merge (idempotent) ──
    sw_settings_path = role_dir / ".claude" / "settings.local.json"
    ws_settings_path = workspace / ".claude" / "settings.local.json"
    if sw_settings_path.is_file():
        ws_settings_path.parent.mkdir(parents=True, exist_ok=True)
        new_settings = json.loads(sw_settings_path.read_text())
        if ws_settings_path.is_file():
            existing = json.loads(ws_settings_path.read_text())
            merged = _deep_merge(existing, new_settings)
            ws_settings_path.write_text(json.dumps(merged, indent=2))
        else:
            ws_settings_path.write_text(json.dumps(new_settings, indent=2))

    # ── flow.yaml + commitment.yaml: deep merge (idempotent) ──
    for fname in ("flow.yaml", "commitment.yaml"):
        src = role_dir / fname
        if not src.is_file():
            continue
        dst = workspace / fname
        new_data = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
        if dst.is_file():
            existing_data = yaml.safe_load(dst.read_text(encoding="utf-8")) or {}
            merged = _deep_merge(existing_data, new_data)
            with dst.open("w", encoding="utf-8") as f:
                yaml.dump(merged, f, default_flow_style=False, allow_unicode=True)
        else:
            shutil.copy2(src, dst)

    _save_assignment(info["app_name"], agent_name, role, channel)

    click.echo(f"✓ Assigned {agent_name} → {role} in {channel}")
    click.echo(f"  Workspace: {workspace}")


# ── socialwares uninstall ──

@main.command()
@click.argument("app_name")
@click.option("--channel", required=True, help="IRC channel")
def uninstall(app_name: str, channel: str) -> None:
    """Uninstall an App."""
    info = _find_install_by_channel(channel)
    if info is None or info["app_name"] != app_name:
        click.echo(f"Error: {app_name} not installed to {channel}")
        raise SystemExit(1)

    # Clean up assignments
    assignments = _load_assignments()
    to_remove = [a for a in assignments if a["app_name"] == app_name and a["channel"] == channel]
    for a in to_remove:
        workspace = _get_agent_workspace(a["agent_name"], channel)
        for fname in ("SOUL.md", "AGENTS.md", "commitment.yaml", "flow.yaml"):
            f = workspace / fname
            if f.is_file():
                f.unlink()
        # Clean up injected skill symlinks (only remove symlinks, not actual directories)
        skills_dir = workspace / ".claude" / "skills"
        if skills_dir.is_dir():
            for item in skills_dir.iterdir():
                if item.is_symlink():
                    item.unlink()

    _remove_install_info(app_name, channel)
    _remove_assignments(app_name, channel)

    click.echo(f"✓ Uninstalled {app_name} from {channel}")


# ── socialwares list ──

@main.command(name="list")
def list_apps() -> None:
    """List installed Apps."""
    installs = _load_installs()
    if not installs:
        click.echo("No apps installed.")
        return
    for info in installs:
        roles = ", ".join(info.get("roles", []))
        click.echo(f"  {info['app_name']} ({info['channel']}) — roles: {roles}")
        click.echo(f"    Path: {info['app_dir']}")


# ── Internal helper functions ──

def _get_agent_workspace(agent_name: str, channel: str) -> Path:
    """Get the workspace path for an agent.

    Priority:
    1. zchat agents.json (production environment)
    2. .socialware/workspace/{channel}/agents/{agent} (local)
    """
    # Try to read the actual zchat state
    state_file = Path.home() / ".local" / "state" / "zchat" / "agents.json"
    if state_file.is_file():
        agents = json.loads(state_file.read_text())
        if agent_name in agents and "workspace" in agents[agent_name]:
            return Path(agents[agent_name]["workspace"])

    # Local workspace
    workspace = _channel_dir(channel) / "agents" / agent_name
    workspace.mkdir(parents=True, exist_ok=True)
    # Ensure .claude directory exists
    claude_dir = workspace / ".claude"
    claude_dir.mkdir(exist_ok=True)
    settings = claude_dir / "settings.local.json"
    if not settings.is_file():
        settings.write_text('{"permissions": {"allow": []}}')
    return workspace


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dicts. Values in override replace base, but dict values are merged recursively."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ── Installation info persistence ──

def _installs_file() -> Path:
    p = _workspace_root() / "installs.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _assignments_file() -> Path:
    p = _workspace_root() / "assignments.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_installs() -> list[dict]:
    f = _installs_file()
    if not f.is_file():
        return []
    return json.loads(f.read_text())


def _save_install_info(app_name: str, app_dir: Path, channel: str, roles: list[str]) -> None:
    installs = _load_installs()
    installs.append({
        "app_name": app_name,
        "app_dir": str(app_dir),
        "channel": channel,
        "roles": roles,
    })
    _installs_file().write_text(json.dumps(installs, indent=2))


def _find_install_by_channel(channel: str) -> dict | None:
    for info in _load_installs():
        if info["channel"] == channel:
            return info
    return None


def _remove_install_info(app_name: str, channel: str) -> None:
    installs = [i for i in _load_installs() if not (i["app_name"] == app_name and i["channel"] == channel)]
    _installs_file().write_text(json.dumps(installs, indent=2))


def _load_assignments() -> list[dict]:
    f = _assignments_file()
    if not f.is_file():
        return []
    return json.loads(f.read_text())


def _save_assignment(app_name: str, agent_name: str, role: str, channel: str) -> None:
    assignments = _load_assignments()
    assignments.append({
        "app_name": app_name,
        "agent_name": agent_name,
        "role": role,
        "channel": channel,
    })
    _assignments_file().write_text(json.dumps(assignments, indent=2))


def _remove_assignments(app_name: str, channel: str) -> None:
    assignments = [a for a in _load_assignments() if not (a["app_name"] == app_name and a["channel"] == channel)]
    _assignments_file().write_text(json.dumps(assignments, indent=2))
