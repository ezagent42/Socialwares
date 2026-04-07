"""Base adapter interface for multi-platform agent launching.

Each adapter reads a deployed role directory (.runtime/agents/{role}/)
and launches the agent using the platform's CLI (TUI) or SDK (programmatic).

v0.3.0: Added MessageEvent / EventKind for platform-agnostic streaming.
"""
from __future__ import annotations

import abc
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator


# --- Serialization (preserved for session recording) ---

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


# --- Role configuration ---

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


# --- Unified message model (v0.3.0) ---

class EventKind(str, Enum):
    """Platform-agnostic message event types.

    Adapters map platform-specific messages to these kinds.
    Consumers (CLI Runner, WebSocket SessionManager) dispatch on kind
    without knowing which LLM platform is behind it.
    """

    # Content
    TEXT_DELTA      = "text_delta"       # Incremental text chunk
    # Tool lifecycle
    TOOL_START      = "tool_start"       # Tool invocation begins
    TOOL_RESULT     = "tool_result"      # Tool execution result
    # Sub-agent (Claude Agent tool)
    SUBAGENT_START  = "subagent_start"   # Sub-agent dispatched
    SUBAGENT_RESULT = "subagent_result"  # Sub-agent completed
    # Session lifecycle
    TURN_START      = "turn_start"       # A turn of reasoning begins
    TURN_END        = "turn_end"         # A turn of reasoning ends
    SESSION_END     = "session_end"      # Session complete (carries session_id)
    # System
    ERROR           = "error"            # Error occurred


@dataclass
class MessageEvent:
    """Platform-agnostic message event.

    All adapters yield MessageEvent from launch_sdk().
    The `raw` field preserves the original SDK object for platform-specific access.
    """
    kind: EventKind
    content: str = ""
    tool_name: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)
    tool_output: str = ""
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    raw: Any = None


# --- Noise filtering (preserved for session recording) ---

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


# --- Session persistence ---

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

    with open(session_file, "w") as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False, default=str)

    return session_file


# --- Proxy env helper ---

def proxy_env() -> dict[str, str]:
    """Full environment with proxy vars ensured for SDK subprocess.

    The SDK subprocess needs the complete environment (PATH, API keys, etc.)
    plus proxy vars for networks that require them (e.g. China).
    """
    env = dict(os.environ)
    # Windows UTF-8 fix
    if os.name == "nt":
        env["PYTHONUTF8"] = "1"
    return env


# --- Base adapter ---

class BaseAdapter(abc.ABC):
    """Abstract base class for agent platform adapters."""

    def __init__(self, config: RoleConfig) -> None:
        self.config = config

    @abc.abstractmethod
    def launch_shell(self) -> None:
        """Launch agent in interactive TUI mode (development)."""
        ...

    @abc.abstractmethod
    async def launch_sdk(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        max_turns: int | None = None,
    ) -> AsyncIterator[MessageEvent]:
        """Launch agent programmatically via SDK.

        Yields MessageEvent instances (platform-agnostic).
        Callers dispatch on event.kind without knowing which LLM is behind it.

        Args:
            prompt: User message.
            session_id: Resume a previous conversation (platform support varies).
            max_turns: Safety limit on tool-use loops.
        """
        ...
        if False:
            yield  # type: ignore
