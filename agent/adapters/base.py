"""Base adapter interface for multi-platform agent launching.

Each adapter reads a deployed role directory (.runtime/agents/{role}/)
and launches the agent using the platform's SDK or CLI.
"""
from __future__ import annotations

import abc
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def log_conversation(project_dir: Path, data: dict) -> None:
    """Log agent interaction to .runtime/data/conversations/.

    Called by SDK adapters during launch_sdk().
    Shell mode uses PostToolUse hook instead.
    """
    # project_dir is .runtime/agents/{role}/
    # conversations dir is .runtime/data/conversations/
    log_dir = project_dir.parent.parent / "data" / "conversations"
    log_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": project_dir.name,
        **data,
    }
    with open(log_dir / "current.jsonl", "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


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
