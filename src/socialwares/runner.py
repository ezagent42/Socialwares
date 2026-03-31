"""Agent 启动器 — 本地启动 agent（TUI / SDK / tmux 多角色）。

对应现有 start.sh + start_agent.py 的 Python 重写。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from socialwares.compiler import ADAPTERS


class Runner:
    """启动编译好的 agent。"""

    def __init__(
        self,
        project_dir: str | Path = ".",
        adapter: str = "claude",
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.runtime_dir = self.project_dir / ".runtime"
        self.adapter = adapter

        if not self.runtime_dir.is_dir():
            raise FileNotFoundError(
                f".runtime/ 不存在。先运行 'socialwares deploy'。"
            )

    def _get_adapter_launcher(self) -> Path:
        """找到适配器的 launcher 脚本（优先 .py，兼容 .sh）。"""
        import socialwares.adapters
        adapters_pkg = Path(socialwares.adapters.__file__).parent
        adapter_name = "kimicode" if self.adapter == "kimi" else self.adapter
        # 优先 Python launcher
        launcher = adapters_pkg / adapter_name / "launch.py"
        if launcher.is_file():
            return launcher
        # 兼容旧的 shell.sh
        shell = adapters_pkg / adapter_name / "shell.sh"
        if shell.is_file():
            return shell
        raise FileNotFoundError(f"适配器 launcher 不存在: {adapters_pkg / adapter_name}")

    def _role_dir(self, role: str) -> Path:
        """获取 role 的 runtime 目录。"""
        d = self.runtime_dir / "agents" / role
        if not d.is_dir():
            available = [p.name for p in (self.runtime_dir / "agents").iterdir() if p.is_dir()]
            raise FileNotFoundError(
                f"角色 '{role}' 不存在。可用角色: {', '.join(available)}"
            )
        return d

    def start(self, role: str) -> None:
        """启动单个 role 的 agent（TUI 模式，exec 替换当前进程）。"""
        role_dir = self._role_dir(role)
        launcher = self._get_adapter_launcher()

        print(f"Starting {role} via {self.adapter} adapter...")
        print(f"  PROJECT_DIR: {role_dir}")
        print()

        if launcher.suffix == ".py":
            os.execvp(sys.executable, [sys.executable, str(launcher), str(role_dir)])
        else:
            os.execv(str(launcher), [str(launcher), str(role_dir)])

    def start_multi(self, roles: list[str]) -> None:
        """多角色启动（tmux 多窗格）。"""
        if not shutil.which("tmux"):
            print("Error: tmux is required for multi-role mode.")
            print("Install: sudo apt install tmux")
            sys.exit(1)

        # 校验所有 role 存在
        for role in roles:
            self._role_dir(role)

        launcher = self._get_adapter_launcher()
        session = f"socialware-{os.getpid()}"

        print(f"Starting {len(roles)} roles in tmux session: {session}")

        def _launch_cmd(role_dir: Path) -> str:
            if launcher.suffix == ".py":
                return f"{sys.executable} {launcher} {role_dir}"
            return f"{launcher} {role_dir}"

        first_dir = self._role_dir(roles[0])
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", session, _launch_cmd(first_dir)],
            check=True,
        )

        for role in roles[1:]:
            role_dir = self._role_dir(role)
            subprocess.run(
                ["tmux", "split-window", "-t", session, "-h", _launch_cmd(role_dir)],
                check=True,
            )
            subprocess.run(["tmux", "select-layout", "-t", session, "tiled"], check=True)

        print("Attaching to tmux session...")
        os.execvp("tmux", ["tmux", "attach", "-t", session])

    def run_sdk(self, role: str, prompt: str) -> None:
        """SDK 模式：发送 prompt 并收集结果。"""
        role_dir = self._role_dir(role)

        # 动态加载适配器
        import importlib
        import socialwares.adapters
        adapters_pkg = Path(socialwares.adapters.__file__).parent

        # 添加 adapters 目录到 path
        sys.path.insert(0, str(adapters_pkg))
        adapter_name = "kimicode" if self.adapter == "kimi" else self.adapter
        sys.path.insert(0, str(adapters_pkg / adapter_name))

        from socialwares.adapters.base import RoleConfig
        config = RoleConfig.from_runtime(role_dir)

        mod = importlib.import_module(f"socialwares.adapters.{adapter_name}.sdk")

        # 找到适配器类
        adapter_cls = None
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (
                isinstance(attr, type)
                and hasattr(attr, "launch_sdk")
                and attr_name != "BaseAdapter"
            ):
                adapter_cls = attr
                break

        if adapter_cls is None:
            raise RuntimeError(f"No adapter class found in {adapter_name}/sdk.py")

        adapter = adapter_cls(config)
        import asyncio
        asyncio.run(self._run_sdk_async(adapter, prompt, role, adapter_name))

    async def _run_sdk_async(self, adapter, prompt: str, role: str, adapter_name: str) -> None:
        """SDK 异步执行。"""
        from socialwares.adapters.base import save_session, is_noise

        ws_root = self.project_dir
        messages = []

        print(f"[SDK] Sending prompt to {role} via {adapter_name}...")
        print()

        try:
            async for message in adapter.launch_sdk(prompt):
                msg = message if isinstance(message, dict) else {"_type": "raw", "content": str(message)}
                if is_noise(msg):
                    continue
                messages.append(msg)
                content = msg.get("content", "") or msg.get("result", "")
                if isinstance(content, str) and content:
                    print(content)
        except NotImplementedError as e:
            print(f"[SDK] Error: {e}")
            return
        except KeyboardInterrupt:
            print("\n[SDK] Interrupted.")

        if messages:
            session_file = save_session(ws_root, role, adapter_name, messages)
            print(f"\n[SDK] Session saved: {session_file}")
            print(f"[SDK] Messages: {len(messages)}")
        else:
            print("[SDK] No messages received.")
