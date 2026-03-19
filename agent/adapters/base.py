"""Base adapter interface for multi-platform agent launching.

Each adapter reads a deployed role directory (.runtime/agents/{role}/)
and launches the agent using the platform's SDK or CLI.
"""
from __future__ import annotations

import abc
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
            soul = soul_path.read_text()

        return cls(
            name=role_dir.name,
            project_dir=role_dir,
            soul=soul,
            skills_dir=role_dir / ".claude" / "skills",
        )


class BaseAdapter(abc.ABC):
    """Abstract base class for agent platform adapters."""

    def __init__(self, config: RoleConfig) -> None:
        self.config = config

    @abc.abstractmethod
    def launch_shell(self) -> None:
        """Launch agent in interactive shell/TUI mode (dev)."""
        ...

    @abc.abstractmethod
    def launch_sdk(self) -> None:
        """Launch agent programmatically via SDK (prod)."""
        ...
