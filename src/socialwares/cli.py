"""CLI — socialwares new / deploy / start / install / assign / uninstall。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import click

SOCIALWARES_HOME = Path.home() / ".socialwares"


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

    # 找到 templates/ 目录
    import socialwares
    pkg_dir = Path(socialwares.__file__).parent
    templates_dir = pkg_dir / "templates"

    if not templates_dir.is_dir():
        click.echo(f"Error: templates not found at {templates_dir}")
        raise SystemExit(1)

    # 复制模板
    shutil.copytree(templates_dir, target)

    # 渲染 socialware.py（简单替换占位符）
    sw_file = target / "socialware.py"
    if sw_file.is_file():
        content = sw_file.read_text()
        content = content.replace("{{APP_NAME}}", name)
        sw_file.write_text(content)

    # 渲染 pyproject.toml
    toml_file = target / "pyproject.toml"
    if toml_file.is_file():
        content = toml_file.read_text()
        content = content.replace("{{APP_NAME}}", name)
        toml_file.write_text(content)

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
        # SDK mode
        runner.run_sdk(roles[0], prompt)
    elif run_all:
        # CI mode: run all evolve skills
        runner.run_sdk(roles[0], "run all checks and report")
    elif len(roles) == 1:
        runner.start(roles[0])
    else:
        runner.start_multi(roles)


# ── socialwares install ──

@main.command()
@click.argument("source")
@click.option("--channel", required=True, help="IRC channel to install to")
def install(source: str, channel: str) -> None:
    """安装 App 到 IRC 频道（git clone + deploy）。"""
    # 从 git URL 提取 app name
    app_name = source.rstrip("/").split("/")[-1]
    if app_name.endswith(".git"):
        app_name = app_name[:-4]

    app_dir = SOCIALWARES_HOME / "apps" / app_name
    if app_dir.exists():
        click.echo(f"App {app_name} already installed at {app_dir}")
        click.echo(f"Use 'socialwares update {app_name}' or uninstall first.")
        raise SystemExit(1)

    # git clone
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
    )
    result = compiler.compile()

    # 记录安装信息
    _save_install_info(app_name, app_dir, channel, list(result.roles.keys()))

    click.echo(f"✓ Installed {app_name} to {channel}")
    click.echo(f"  Roles: {', '.join(result.roles.keys())}")
    click.echo(f"  Now assign roles: socialwares assign <agent> --role <role> --channel {channel}")


# ── socialwares assign ──

@main.command()
@click.argument("agent_name")
@click.option("--role", required=True, help="Role to assign")
@click.option("--channel", required=True, help="IRC channel")
def assign(agent_name: str, role: str, channel: str) -> None:
    """给 IRC 频道中的 agent 分配 role。"""
    # 找到该 channel 安装的 app
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

    # 获取 agent workspace（mock 或真实 zchat）
    workspace = _get_agent_workspace(agent_name)

    # 注入 SOUL.md
    prompt_file = "SOUL.md"  # TODO: 从 adapter config 读取
    src_prompt = role_dir / prompt_file
    if src_prompt.is_file():
        shutil.copy2(src_prompt, workspace / prompt_file)

    # 注入 skills（symlink）
    src_skills = role_dir / ".claude" / "skills"
    dst_skills = workspace / ".claude" / "skills"
    if src_skills.is_dir():
        dst_skills.parent.mkdir(parents=True, exist_ok=True)
        if dst_skills.is_symlink() or dst_skills.exists():
            if dst_skills.is_symlink():
                dst_skills.unlink()
            else:
                shutil.rmtree(dst_skills)
        dst_skills.symlink_to(src_skills.resolve())

    # 注入 hooks（merge，不覆盖 zchat 已有配置）
    sw_settings_path = role_dir / ".claude" / "settings.local.json"
    ws_settings_path = workspace / ".claude" / "settings.local.json"
    if sw_settings_path.is_file():
        ws_settings_path.parent.mkdir(parents=True, exist_ok=True)
        if ws_settings_path.is_file():
            existing = json.loads(ws_settings_path.read_text())
            new = json.loads(sw_settings_path.read_text())
            merged = _deep_merge(existing, new)
            ws_settings_path.write_text(json.dumps(merged, indent=2))
        else:
            shutil.copy2(sw_settings_path, ws_settings_path)

    # 注入 commitment.yaml + flow.yaml
    for fname in ("commitment.yaml", "flow.yaml"):
        src = role_dir / fname
        if src.is_file():
            shutil.copy2(src, workspace / fname)

    # 记录 assignment
    _save_assignment(info["app_name"], agent_name, role, channel)

    click.echo(f"✓ Assigned {agent_name} → {role} in {channel}")


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
        workspace = _get_agent_workspace(a["agent_name"])
        # 清理注入的文件
        for fname in ("SOUL.md", "AGENTS.md", "commitment.yaml", "flow.yaml"):
            f = workspace / fname
            if f.is_file():
                f.unlink()
        skills = workspace / ".claude" / "skills"
        if skills.is_symlink():
            skills.unlink()

    # 清理安装记录
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


# ── 内部辅助函数 ──

def _get_agent_workspace(agent_name: str) -> Path:
    """获取 zchat agent 的 workspace 路径。

    当前：mock 实现。
    未来：读取 ~/.local/state/zchat/agents.json。
    """
    # 尝试读取真实 zchat state
    state_file = Path.home() / ".local" / "state" / "zchat" / "agents.json"
    if state_file.is_file():
        agents = json.loads(state_file.read_text())
        if agent_name in agents and "workspace" in agents[agent_name]:
            return Path(agents[agent_name]["workspace"])

    # Mock fallback
    mock_dir = SOCIALWARES_HOME / "mock_agents" / agent_name
    mock_dir.mkdir(parents=True, exist_ok=True)
    claude_dir = mock_dir / ".claude"
    claude_dir.mkdir(exist_ok=True)
    settings = claude_dir / "settings.local.json"
    if not settings.is_file():
        settings.write_text('{"permissions": {"allow": []}}')
    return mock_dir


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
    return SOCIALWARES_HOME / "installs.json"


def _assignments_file() -> Path:
    return SOCIALWARES_HOME / "assignments.json"


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
    _installs_file().parent.mkdir(parents=True, exist_ok=True)
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
    _assignments_file().parent.mkdir(parents=True, exist_ok=True)
    _assignments_file().write_text(json.dumps(assignments, indent=2))


def _remove_assignments(app_name: str, channel: str) -> None:
    assignments = [a for a in _load_assignments() if not (a["app_name"] == app_name and a["channel"] == channel)]
    _assignments_file().write_text(json.dumps(assignments, indent=2))
