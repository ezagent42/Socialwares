"""Tests for AgentForge API endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


class TestHealth:
    def test_health(self):
        assert client.get("/health").status_code == 200


class TestAdapters:
    def test_list_adapters(self):
        r = client.get("/adapters")
        assert r.status_code == 200
        names = {a["name"] for a in r.json()["adapters"]}
        assert len(names) >= 1
        for a in r.json()["adapters"]:
            assert "available" in a


class TestSession:
    def test_no_session_initially(self):
        client.delete("/session")
        r = client.get("/session")
        assert r.json()["active"] is False

    def test_delete_session(self):
        assert client.delete("/session").json()["status"] == "closed"

    def test_chat_without_session(self):
        client.delete("/session")
        assert client.post("/chat", json={"message": "hi"}).status_code == 400


class TestPrimitives:
    def test_get_roles(self):
        r = client.get("/roles")
        assert "roles" in r.json()
        assert "default" in r.json()["roles"]

    def test_get_role_detail(self):
        r = client.get("/roles/default")
        assert r.status_code == 200
        assert "soul" in r.json()

    def test_get_role_not_found(self):
        assert client.get("/roles/nonexistent").status_code == 404

    def test_get_flows(self):
        assert "flows" in client.get("/flows").json()

    def test_get_flows_registry(self):
        r = client.get("/flows/registry")
        assert r.status_code == 200

    def test_get_scope(self):
        assert "soul" in client.get("/scope").json()

    def test_get_commitments(self):
        assert client.get("/commitments").status_code == 200


class TestMetrics:
    def test_get_metrics(self):
        r = client.get("/metrics")
        assert r.status_code == 200
        assert "metrics" in r.json()

    def test_post_eval(self):
        r = client.post("/eval", json={"commitment_id": "all"})
        assert r.status_code == 200
        assert "results" in r.json()


class TestWorkspaces:
    def test_list_workspaces(self):
        r = client.get("/workspaces")
        assert r.status_code == 200
        assert "workspaces" in r.json()

    def test_delete_nonexistent(self):
        assert client.delete("/workspaces/nonexistent/ws").status_code == 404


class TestFlowState:
    def test_get_state(self):
        r = client.get("/flows/state")
        assert r.status_code == 200

    def test_get_state_specific(self):
        r = client.get("/flows/state?flow=agent_review")
        assert r.json()["flow"] == "agent_review"

    def test_transition_invalid_flow(self):
        assert client.post("/flows/transition", json={"flow": "x", "action": "y"}).status_code == 404


class TestZChat:
    def test_discover(self):
        r = client.get("/zchat/discover")
        assert r.status_code == 200
        assert "soul" in r.json()

    def test_receive(self):
        r = client.post("/zchat/receive", json={
            "from": "a/r", "to": "b/r", "intent": "ping", "payload": {},
        })
        assert r.status_code == 200
