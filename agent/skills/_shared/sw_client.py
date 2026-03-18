"""Socialware App API client.

Generic HTTP client for calling SW App APIs.
All SW Apps expose CRUD + action endpoints following four-primitive pattern.
"""
from __future__ import annotations

import json
import sys
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError


class SWClient:
    """Generic Socialware App API client."""

    def __init__(self, base_url: str, identity: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.identity = identity

    def request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send HTTP request to SW App API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., /tasks, /tasks/123)
            data: Request body (JSON)

        Returns:
            Parsed JSON response
        """
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.identity:
            headers["X-Identity"] = self.identity

        body = json.dumps(data).encode() if data else None
        req = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(req) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            error_body = e.read().decode()
            print(f"API Error {e.code}: {error_body}", file=sys.stderr)
            return {"error": e.code, "detail": error_body}


def create_client(config: dict[str, Any]) -> SWClient:
    """Create SWClient from skill config."""
    return SWClient(
        base_url=config.get("api_url", "http://localhost:8000"),
        identity=config.get("identity"),
    )
