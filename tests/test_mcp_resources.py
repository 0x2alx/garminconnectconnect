"""Tests for MCP resources."""
import asyncio
import pytest
from garminconnect.mcp.server import create_mcp_server


@pytest.fixture
def mcp():
    return create_mcp_server("postgresql+psycopg://fake:fake@localhost/fake")


def test_instructions_resource_registered(mcp):
    loop = asyncio.new_event_loop()
    try:
        resources = loop.run_until_complete(mcp.list_resources())
    finally:
        loop.close()
    uris = [str(r.uri) for r in resources]
    assert any("instructions" in u for u in uris)


def test_tables_resource_registered(mcp):
    loop = asyncio.new_event_loop()
    try:
        resources = loop.run_until_complete(mcp.list_resources())
    finally:
        loop.close()
    uris = [str(r.uri) for r in resources]
    assert any("tables" in u for u in uris)


def test_queries_resource_registered(mcp):
    loop = asyncio.new_event_loop()
    try:
        resources = loop.run_until_complete(mcp.list_resources())
    finally:
        loop.close()
    uris = [str(r.uri) for r in resources]
    assert any("queries" in u for u in uris)
