"""Base adapter interface for multi-platform agent launching.

Each adapter reads a deployed role directory (.runtime/agents/{role}/)
and launches the agent using the platform's CLI (TUI) or SDK (programmatic).
"""
from __future__ import annotations

import abc
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator


def serialize(obj: Any) -> Any:
    """Recursively serialize SDK message objects to JSON-safe dicts.

    Follows autoservice pattern: preserves structure with _type metadata.
    All adapters use this for consistent session recording.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    if hasattr(obj, '__dict__'):
        return {
            '_type': obj.__class__.__name__,
            **{k: serialize(v) for k, v in vars(obj).items()}
        }
    return str(obj)


@dataclass
class RoleConfig:
    """Deployed role configuration."""

    name: str
    project_dir: Path
    soul: str
    skills_dir: Path
    workspace_root: Path

    @classmethod
    def from_runtime(cls, role_dir: str | Path) -> RoleConfig:
        """Load role config from a deployed .runtime/agents/{role}/ directory."""
        role_dir = Path(role_dir)
        soul = ""
        # Try SOUL.md (claude) or AGENTS.md (codex/kimi)
        for prompt_file in ["SOUL.md", "AGENTS.md"]:
            path = role_dir / prompt_file
            if path.exists():
                soul = path.read_text(encoding="utf-8")
                break

        # Read workspace root
        workspace_root = role_dir.parent.parent.parent  # default fallback
        ws_file = role_dir / ".workspace_root"
        if ws_file.exists():
            workspace_root = Path(ws_file.read_text(encoding="utf-8").strip())

        # Find skills dir (adapter-specific)
        skills_dir = role_dir / ".claude" / "skills"
        if not skills_dir.exists():
            skills_dir = role_dir / ".agents" / "skills"

        return cls(
            name=role_dir.name,
            project_dir=role_dir,
            soul=soul,
            skills_dir=skills_dir,
            workspace_root=workspace_root,
        )


# Message types to skip when recording sessions — system noise, not conversation content
_SKIP_TYPES = ("ratelimit", "hook", "init", "system")


def is_noise(msg: dict) -> bool:
    """Check if a serialized SDK message is system noise (not conversation content).

    Filters out rate limit events, hook notifications, init messages, etc.
    Used by both start_agent.py and run_auto.py for consistent session recording.
    """
    msg_type = msg.get("_type", "").lower()
    subtype = msg.get("subtype", "").lower() if isinstance(msg.get("subtype"), str) else ""
    combined = msg_type + subtype
    return any(skip in combined for skip in _SKIP_TYPES)


def save_session(workspace_root: Path, role: str, adapter: str, messages: list[dict]) -> Path:
    """Save a complete SDK session to .runtime/data/sessions/.

    Returns the path to the saved session file.
    """
    sessions_dir = workspace_root / ".runtime" / "data" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    session_id = f"{role}_session_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    session_file = sessions_dir / f"{session_id}.json"

    session_data = {
        "session_id": session_id,
        "role": role,
        "adapter": adapter,
        "started_at": timestamp.isoformat(),
        "message_count": len(messages),
        "messages": messages,
    }

    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False, default=str)

    return session_file


class BaseAdapter(abc.ABC):
    """Abstract base class for agent platform adapters."""

    def __init__(self, config: RoleConfig) -> None:
        self.config = config

    @abc.abstractmethod
    def launch_shell(self) -> None:
        """Launch agent in interactive TUI mode (development)."""
        ...

    @abc.abstractmethod
    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        """Launch agent programmatically via SDK (production).

        Yields raw message objects from the platform SDK.
        Caller is responsible for consuming and saving.
        """
        ...
        # Make it a generator
        if False:
            yield
