"""Tests for ZChat protocol."""
from __future__ import annotations

from src.zchat import ZChatMessage, ZChatRouter


class TestMessage:
    def test_create(self):
        m = ZChatMessage(from_app="a", from_role="r1", to_app="b", to_role="r2", intent="ping", payload={})
        assert m.intent == "ping"

    def test_to_dict(self):
        d = ZChatMessage(from_app="a", from_role="r", to_app="b", to_role="r", intent="t", payload={}).to_dict()
        assert d["from"] == "a/r"
        assert d["intent"] == "t"

    def test_from_dict(self):
        m = ZChatMessage.from_dict({"from": "a/r1", "to": "b/r2", "intent": "p", "payload": {"x": 1}})
        assert m.from_app == "a"
        assert m.payload == {"x": 1}

    def test_roundtrip(self):
        orig = ZChatMessage(from_app="a", from_role="r", to_app="b", to_role="r", intent="t", payload={"k": "v"})
        restored = ZChatMessage.from_dict(orig.to_dict())
        assert restored.intent == orig.intent
        assert restored.payload == orig.payload


class TestRouter:
    def test_register(self):
        r = ZChatRouter()
        r.register("ping", lambda m: "pong")
        assert "ping" in r.handlers

    def test_dispatch(self):
        r = ZChatRouter()
        r.register("ping", lambda m: "pong")
        m = ZChatMessage(from_app="a", from_role="r", to_app="b", to_role="r", intent="ping", payload={})
        assert r.dispatch(m) == "pong"

    def test_unknown(self):
        assert "error" in ZChatRouter().dispatch(
            ZChatMessage(from_app="a", from_role="r", to_app="b", to_role="r", intent="x", payload={})
        )
