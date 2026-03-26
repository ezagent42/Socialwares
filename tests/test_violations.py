"""Tests for the violations queue and API endpoints."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.app import app


client = TestClient(app)


class TestViolationsAPI:
    """Test violations REST endpoints."""

    def test_list_violations_empty(self):
        resp = client.get("/violations")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_health_still_works(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
