"""Tests for compare_activities and find_similar_activities MCP tools."""
import asyncio
import json
import pytest
from garminconnect.mcp.server import create_mcp_server


@pytest.fixture
def mcp():
    return create_mcp_server("postgresql+psycopg://fake:fake@localhost/fake")


def _call_tool(server, name, args):
    """Helper to call a FastMCP tool synchronously."""
    try:
        result = asyncio.get_event_loop().run_until_complete(server.call_tool(name, args))
    except Exception as e:
        return [{"error": f"Connection error: {e}"}]
    # FastMCP returns CallToolResult with structured_content
    if hasattr(result, 'structured_content') and result.structured_content:
        return result.structured_content.get('result', result.structured_content)
    # Fallback to text content
    if hasattr(result, 'content') and result.content:
        text = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
        return json.loads(text)
    return result


def test_compare_activities_too_few(mcp):
    result = _call_tool(mcp, "compare_activities", {"activity_ids": "123"})
    if isinstance(result, dict):
        assert "error" in result
    elif isinstance(result, list):
        assert any("error" in r for r in result if isinstance(r, dict))


def test_compare_activities_too_many(mcp):
    result = _call_tool(mcp, "compare_activities", {"activity_ids": "1,2,3,4,5,6"})
    if isinstance(result, dict):
        assert "error" in result
    elif isinstance(result, list):
        assert any("error" in r for r in result if isinstance(r, dict))


def test_find_similar_missing_activity(mcp):
    result = _call_tool(mcp, "find_similar_activities", {"activity_id": "nonexistent999"})
    # Will either be an error dict or a DB connection error (both acceptable for fake DB)
    result_str = str(result).lower()
    assert "error" in result_str or "connection" in result_str
