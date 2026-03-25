"""Base adapter interface for multi-platform agent launching.

Each adapter reads a deployed role directory (.runtime/agents/{role}/)
and launches the agent using the platform's SDK or CLI.

Lifecycle: connect() → query() × N → disconnect()
"""
from __future__ import annotations

import abc
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RoleConfig:
    """Deployed role configuration."""

    name: str
    project_dir: Path
    soul: str
    skills_dir: Path

    @classmethod
    def from_runtime(cls, role_dir: str | Path) -> RoleConfig:
        """Load role config from a deployed .runtime/agents/{role}/ directory."""
        role_dir = Path(role_dir)
        soul = ""
        soul_path = role_dir / "SOUL.md"
        if soul_path.exists():
            soul = soul_path.read_text(encoding="utf-8")

        return cls(
            name=role_dir.name,
            project_dir=role_dir,
            soul=soul,
            skills_dir=role_dir / ".claude" / "skills",
        )


class BaseAdapter(abc.ABC):
    """Abstract base class for agent platform adapters.

    Lifecycle:
        adapter = SomeAdapter(config)
        await adapter.connect()       # Start long-running agent session
        msgs = await adapter.query()  # Send messages (multiple times)
        await adapter.disconnect()    # Close session
    """

    def __init__(self, config: RoleConfig) -> None:
        self.config = config
        self._connected = False

    @abc.abstractmethod
    def launch_shell(self) -> None:
        """Launch agent in interactive shell/TUI mode (dev)."""
        ...

    @abc.abstractmethod
    def launch_sdk(self) -> None:
        """Launch agent programmatically via SDK (prod)."""
        ...

    @abc.abstractmethod
    async def connect(self) -> None:
        """Start a long-running agent session."""
        ...

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Close the agent session."""
        ...

    @abc.abstractmethod
    async def query(self, prompt: str) -> list[dict]:
        """Send a prompt within the active session, return response messages.
        Returns: [{"type": "text", "text": "..."}]
        """
        ...

    @classmethod
    @abc.abstractmethod
    def is_available(cls) -> bool:
        """Check if this adapter's runtime is installed on the system."""
        ...
