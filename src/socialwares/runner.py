"""Agent runner — launch agents locally (TUI / SDK / tmux multi-role).

Python rewrite of the existing start.sh + start_agent.py.
v0.3.0: Consumes MessageEvent from adapters.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from socialwares.compiler import ADAPTERS


class Runner:
    """Launch a compiled agent."""

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
                f".runtime/ does not exist. Run 'socialwares deploy' first."
            )

    def _get_adapter_launcher(self) -> Path:
        """Find the adapter's launcher script (prefer .py, fall back to .sh)."""
        import socialwares.adapters
        adapters_pkg = Path(socialwares.adapters.__file__).parent
        adapter_name = "kimicode" if self.adapter == "kimi" else self.adapter
        # Prefer Python launcher
        launcher = adapters_pkg / adapter_name / "launch.py"
        if launcher.is_file():
            return launcher
        # Fall back to legacy shell.sh
        shell = adapters_pkg / adapter_name / "shell.sh"
        if shell.is_file():
            return shell
        raise FileNotFoundError(f"Adapter launcher not found: {adapters_pkg / adapter_name}")

    def _role_dir(self, role: str) -> Path:
        """Get the runtime directory for a role."""
        d = self.runtime_dir / "agents" / role
        if not d.is_dir():
            available = [p.name for p in (self.runtime_dir / "agents").iterdir() if p.is_dir()]
            raise FileNotFoundError(
                f"Role '{role}' does not exist. Available roles: {', '.join(available)}"
            )
        return d

    def start(self, role: str) -> None:
        """Start a single role's agent (TUI mode, exec replaces current process)."""
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
        """Multi-role startup (tmux multi-pane)."""
        if not shutil.which("tmux"):
            print("Error: tmux is required for multi-role mode.")
            print("Install: sudo apt install tmux")
            sys.exit(1)

        # Validate that all roles exist
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
        """SDK mode: send a prompt and collect results."""
        role_dir = self._role_dir(role)

        # Dynamically load adapter
        import importlib
        import socialwares.adapters
        adapters_pkg = Path(socialwares.adapters.__file__).parent

        # Add adapters directory to path
        sys.path.insert(0, str(adapters_pkg))
        adapter_name = "kimicode" if self.adapter == "kimi" else self.adapter
        sys.path.insert(0, str(adapters_pkg / adapter_name))

        from socialwares.adapters.base import RoleConfig
        config = RoleConfig.from_runtime(role_dir)

        mod = importlib.import_module(f"socialwares.adapters.{adapter_name}.sdk")

        # Find the adapter class
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
        """SDK async execution — consumes MessageEvent from adapter."""
        from socialwares.adapters.base import save_session, serialize, EventKind

        ws_root = self.project_dir
        messages: list[dict] = []

        print(f"[SDK] Sending prompt to {role} via {adapter_name}...")
        print()

        try:
            async for event in adapter.launch_sdk(prompt):
                # Record raw event for session persistence
                messages.append(serialize(event))

                # Print based on event kind
                if event.kind == EventKind.TEXT_DELTA and event.content:
                    print(event.content, end="", flush=True)
                elif event.kind == EventKind.TOOL_START:
                    print(f"\n[tool] {event.tool_name}", flush=True)
                elif event.kind == EventKind.SUBAGENT_START:
                    print(f"\n[subagent] {event.tool_name}", flush=True)
                elif event.kind == EventKind.SESSION_END:
                    print(f"\n[session] {event.session_id}", flush=True)
                elif event.kind == EventKind.ERROR:
                    print(f"\n[error] {event.content}", flush=True)

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
