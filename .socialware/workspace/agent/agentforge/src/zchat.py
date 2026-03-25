"""ZChat — Agent-to-Agent communication protocol.

Defines message format and routing for inter-App communication.
Transport layer (Zenoh/HTTP) is pluggable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ZChatMessage:
    """A message between two Socialware App agents."""
    from_app: str
    from_role: str
    to_app: str
    to_role: str
    intent: str
    payload: dict[str, Any] = field(default_factory=dict)
    reply_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": f"{self.from_app}/{self.from_role}",
            "to": f"{self.to_app}/{self.to_role}",
            "intent": self.intent,
            "payload": self.payload,
            "reply_to": self.reply_to,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ZChatMessage:
        from_parts = d["from"].split("/", 1)
        to_parts = d["to"].split("/", 1)
        return cls(
            from_app=from_parts[0],
            from_role=from_parts[1] if len(from_parts) > 1 else "default",
            to_app=to_parts[0],
            to_role=to_parts[1] if len(to_parts) > 1 else "default",
            intent=d["intent"],
            payload=d.get("payload", {}),
            reply_to=d.get("reply_to"),
        )


class ZChatRouter:
    """Routes incoming ZChat messages to registered handlers."""

    def __init__(self):
        self.handlers: dict[str, Callable] = {}

    def register(self, intent: str, handler: Callable) -> None:
        self.handlers[intent] = handler

    def dispatch(self, message: ZChatMessage) -> Any:
        handler = self.handlers.get(message.intent)
        if handler:
            return handler(message)
        return {"error": f"No handler for intent: {message.intent}"}
