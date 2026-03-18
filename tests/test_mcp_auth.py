"""Tests for MCP server bearer token authentication."""
from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from garminconnect.mcp.server import BearerAuthMiddleware


def _make_app(api_key: str = "") -> BearerAuthMiddleware:
    """Create a minimal Starlette app wrapped with BearerAuthMiddleware."""
    async def homepage(request):
        return JSONResponse({"status": "ok"})

    app = Starlette(routes=[Route("/", homepage)])
    return BearerAuthMiddleware(app, api_key=api_key)


class TestBearerAuthMiddleware:
    def test_no_api_key_allows_all_requests(self):
        """When api_key is empty, all requests pass through (dev mode)."""
        app = _make_app(api_key="")
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_valid_bearer_token_passes(self):
        """Requests with correct bearer token are allowed."""
        app = _make_app(api_key="test-secret-key")
        client = TestClient(app)
        resp = client.get("/", headers={"Authorization": "Bearer test-secret-key"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_missing_auth_header_returns_401(self):
        """Requests without auth header return 401."""
        app = _make_app(api_key="test-secret-key")
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 401
        assert "Unauthorized" in resp.json()["error"]

    def test_wrong_token_returns_401(self):
        """Requests with wrong token return 401."""
        app = _make_app(api_key="test-secret-key")
        client = TestClient(app)
        resp = client.get("/", headers={"Authorization": "Bearer wrong-key"})
        assert resp.status_code == 401

    def test_non_bearer_auth_returns_401(self):
        """Non-bearer auth schemes return 401."""
        app = _make_app(api_key="test-secret-key")
        client = TestClient(app)
        resp = client.get("/", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert resp.status_code == 401

    def test_empty_bearer_token_returns_401(self):
        """Empty bearer token returns 401."""
        app = _make_app(api_key="test-secret-key")
        client = TestClient(app)
        resp = client.get("/", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401
