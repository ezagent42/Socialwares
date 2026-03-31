"""CLI — socialwares new / deploy / start / install / assign / uninstall。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import click


def _workspace_root() -> Path:
    """返回 .socialware/workspace/ 目录。"""
    return Path.cwd() / ".socialware" / "workspace"


def _channel_dir(channel: str) -> Path:
    """返回频道目录。去掉 # 前缀。"""
    name = channel.lstrip("#")
    return _workspace_root() / name


def _load_config(project_dir: Path) -> dict:
    """从 pyproject.toml 读取 [tool.socialwares] 配置。"""
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
    """Socialwares — 构建 Socialware App 的框架。"""


# ── socialwares new ──

@main.command()
@click.argument("name")
def new(name: str) -> None:
    """创建新项目。"""
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

    shutil.copytree(templates_dir, target)

    # 渲染占位符
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
    """编译四原语 → .runtime/"""
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


# ── socialwares start ──

@main.command()
@click.option("--role", required=True, help="Role name (comma-separated for multi)")
@click.option("--adapter", default=None, help="LLM adapter")
@click.option("--prompt", default=None, help="Prompt for SDK mode")
@click.option("--run-all", is_flag=True, help="Run all evolve checks (CI mode)")
def start(role: str, adapter: str | None, prompt: str | None, run_all: bool) -> None:
    """启动 agent（本地开发）。"""
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
    """安装 App 到 IRC 频道（git clone + deploy）。"""
    app_name = source.rstrip("/").split("/")[-1]
    if app_name.endswith(".git"):
        app_name = app_name[:-4]

    # 安装到 .socialware/workspace/{channel}/apps/{app}/
    if install_path:
        app_dir = Path(install_path)
    else:
        app_dir = _channel_dir(channel) / "apps" / app_name

    if app_dir.exists():
        # 目录存在但 installs.json 没记录 → 残留，清掉重装
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
    """给 IRC 频道中的 agent 分配 role。"""
    # 找到 app
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

    # agent workspace 路径
    if agent_path:
        workspace = Path(agent_path)
        workspace.mkdir(parents=True, exist_ok=True)
    else:
        workspace = _get_agent_workspace(agent_name, channel)

    # 注入 SOUL.md（覆盖）
    for prompt_file in ("SOUL.md", "AGENTS.md"):
        src = role_dir / prompt_file
        if src.is_file():
            shutil.copy2(src, workspace / prompt_file)

    # 注入 skills（逐个 symlink，追加不替换）
    src_skills = role_dir / ".claude" / "skills"
    if src_skills.is_dir():
        dst_skills = workspace / ".claude" / "skills"
        dst_skills.mkdir(parents=True, exist_ok=True)
        for skill_link in src_skills.iterdir():
            dst_link = dst_skills / skill_link.name
            if dst_link.is_symlink():
                dst_link.unlink()
            elif dst_link.exists():
                shutil.rmtree(dst_link)
            # 解析源 symlink 的实际目标
            if skill_link.is_symlink():
                dst_link.symlink_to(skill_link.resolve())
            else:
                dst_link.symlink_to(skill_link.resolve())

    # 注入 hooks（merge，不覆盖已有配置）
    sw_settings_path = role_dir / ".claude" / "settings.local.json"
    ws_settings_path = workspace / ".claude" / "settings.local.json"
    if sw_settings_path.is_file():
        ws_settings_path.parent.mkdir(parents=True, exist_ok=True)
        if ws_settings_path.is_file():
            existing = json.loads(ws_settings_path.read_text())
            new_settings = json.loads(sw_settings_path.read_text())
            merged = _deep_merge(existing, new_settings)
            ws_settings_path.write_text(json.dumps(merged, indent=2))
        else:
            shutil.copy2(sw_settings_path, ws_settings_path)

    # 注入 commitment.yaml + flow.yaml
    for fname in ("commitment.yaml", "flow.yaml"):
        src = role_dir / fname
        if src.is_file():
            shutil.copy2(src, workspace / fname)

    _save_assignment(info["app_name"], agent_name, role, channel)

    click.echo(f"✓ Assigned {agent_name} → {role} in {channel}")
    click.echo(f"  Workspace: {workspace}")


# ── socialwares uninstall ──

@main.command()
@click.argument("app_name")
@click.option("--channel", required=True, help="IRC channel")
def uninstall(app_name: str, channel: str) -> None:
    """卸载 App。"""
    info = _find_install_by_channel(channel)
    if info is None or info["app_name"] != app_name:
        click.echo(f"Error: {app_name} not installed to {channel}")
        raise SystemExit(1)

    # 清理 assignments
    assignments = _load_assignments()
    to_remove = [a for a in assignments if a["app_name"] == app_name and a["channel"] == channel]
    for a in to_remove:
        workspace = _get_agent_workspace(a["agent_name"], channel)
        for fname in ("SOUL.md", "AGENTS.md", "commitment.yaml", "flow.yaml"):
            f = workspace / fname
            if f.is_file():
                f.unlink()
        # 清理注入的 skill symlinks（只删 symlink，不删实际目录）
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
    """列出已安装的 App。"""
    installs = _load_installs()
    if not installs:
        click.echo("No apps installed.")
        return
    for info in installs:
        roles = ", ".join(info.get("roles", []))
        click.echo(f"  {info['app_name']} ({info['channel']}) — roles: {roles}")
        click.echo(f"    Path: {info['app_dir']}")


# ── 内部辅助函数 ──

def _get_agent_workspace(agent_name: str, channel: str) -> Path:
    """获取 agent 的 workspace 路径。

    优先级：
    1. zchat agents.json（真实环境）
    2. .socialware/workspace/{channel}/agents/{agent}（本地）
    """
    # 尝试读取真实 zchat state
    state_file = Path.home() / ".local" / "state" / "zchat" / "agents.json"
    if state_file.is_file():
        agents = json.loads(state_file.read_text())
        if agent_name in agents and "workspace" in agents[agent_name]:
            return Path(agents[agent_name]["workspace"])

    # 本地 workspace
    workspace = _channel_dir(channel) / "agents" / agent_name
    workspace.mkdir(parents=True, exist_ok=True)
    # 确保 .claude 目录存在
    claude_dir = workspace / ".claude"
    claude_dir.mkdir(exist_ok=True)
    settings = claude_dir / "settings.local.json"
    if not settings.is_file():
        settings.write_text('{"permissions": {"allow": []}}')
    return workspace


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并两个 dict。override 的值覆盖 base，但 dict 类型递归合并。"""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ── 安装信息持久化 ──

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
