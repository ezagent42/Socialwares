"""Chat history manager — saves conversation to JSON files.

Each session gets a JSON file at data/chat/{session_id}.json.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ChatMessage:
    role: str  # "user" | "agent" | "system"
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ChatSession:
    session_id: str
    agent_role: str
    adapter: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add_message(self, role: str, content: str) -> ChatMessage:
        msg = ChatMessage(role=role, content=content)
        self.messages.append(msg)
        return msg

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "agent_role": self.agent_role,
            "adapter": self.adapter,
            "created_at": self.created_at,
            "messages": [asdict(m) for m in self.messages],
        }

    @classmethod
    def from_dict(cls, d: dict) -> ChatSession:
        session = cls(
            session_id=d["session_id"],
            agent_role=d["agent_role"],
            adapter=d["adapter"],
            created_at=d.get("created_at", 0),
        )
        for m in d.get("messages", []):
            session.messages.append(ChatMessage(**m))
        return session


class ChatHistoryManager:
    """Manages chat history as JSON files in data/chat/."""

    def __init__(self, data_dir: str | Path):
        self.chat_dir = Path(data_dir) / "chat"
        self.chat_dir.mkdir(parents=True, exist_ok=True)
        self._current: ChatSession | None = None

    def new_session(self, role: str, adapter: str) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            session_id=str(uuid.uuid4())[:8],
            agent_role=role,
            adapter=adapter,
        )
        self._current = session
        self._save()
        return session

    def add_user_message(self, content: str) -> None:
        if self._current:
            self._current.add_message("user", content)
            self._save()

    def add_agent_message(self, content: str) -> None:
        if self._current:
            self._current.add_message("agent", content)
            self._save()

    def add_system_message(self, content: str) -> None:
        if self._current:
            self._current.add_message("system", content)
            self._save()

    def close_session(self) -> None:
        if self._current:
            self.add_system_message("Session closed")
            self._current = None

    def get_current(self) -> ChatSession | None:
        return self._current

    def list_sessions(self) -> list[dict]:
        """List all saved chat sessions (summary only)."""
        sessions = []
        for f in sorted(self.chat_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                sessions.append({
                    "session_id": data["session_id"],
                    "agent_role": data["agent_role"],
                    "adapter": data["adapter"],
                    "created_at": data.get("created_at"),
                    "message_count": len(data.get("messages", [])),
                    "file": f.name,
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return sessions

    def load_session(self, session_id: str) -> ChatSession | None:
        """Load a session from file."""
        path = self.chat_dir / f"{session_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ChatSession.from_dict(data)

    def _save(self) -> None:
        if not self._current:
            return
        path = self.chat_dir / f"{self._current.session_id}.json"
        path.write_text(
            json.dumps(self._current.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
