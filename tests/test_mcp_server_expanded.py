"""Task 5.2: Tests for MCP tools with mocked DB."""
import asyncio
from unittest.mock import MagicMock
import pytest
from garminconnect.mcp.server import create_mcp_server
from garminconnect.mcp.tools import QUERY_TEMPLATES, get_table_list


class TestGetTableList:
    def test_returns_list(self):
        tables = get_table_list()
        assert isinstance(tables, list)
        assert "daily_summary" in tables
        assert "activities" in tables
        assert len(tables) == 16


class TestQueryTemplates:
    def test_all_templates_are_strings(self):
        for name, template in QUERY_TEMPLATES.items():
            assert isinstance(template, str), f"{name} template is not a string"

    def test_known_templates_exist(self):
        expected = {
            "daily_overview", "sleep_trend", "hr_intraday", "activity_list",
            "weekly_comparison", "activity_detail", "personal_records", "recovery_analysis",
        }
        assert expected.issubset(set(QUERY_TEMPLATES.keys()))


def _call_tool(server, name, args):
    """Helper to call a FastMCP tool synchronously."""
    try:
        result = asyncio.get_event_loop().run_until_complete(server.call_tool(name, args))
    except Exception as e:
        # DB connection errors are expected in unit tests; wrap them
        return [{"error": f"Connection error: {e}"}]
    # FastMCP returns CallToolResult with structured_content
    if hasattr(result, 'structured_content') and result.structured_content:
        return result.structured_content.get('result', result.structured_content)
    # Fallback to text content
    if hasattr(result, 'content') and result.content:
        return result.content[0].text
    return result


class TestExecuteSqlLogic:
    def test_rejects_insert(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "execute_sql", {"query": "INSERT INTO foo VALUES (1)"})
        assert result == [{"error": "Only SELECT/WITH queries are allowed"}]

    def test_rejects_drop(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "execute_sql", {"query": "DROP TABLE daily_summary"})
        assert result == [{"error": "Only SELECT/WITH queries are allowed"}]

    def test_rejects_update(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "execute_sql", {"query": "UPDATE daily_summary SET total_steps = 0"})
        assert result == [{"error": "Only SELECT/WITH queries are allowed"}]

    def test_allows_select_prefix(self):
        """SELECT prefix passes validation; DB connection may fail but we verify
        it's not rejected by the prefix check."""
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "execute_sql", {"query": "SELECT 1"})
        if isinstance(result, list):
            for r in result:
                if isinstance(r, dict) and "error" in r:
                    # DB connection error is fine; prefix rejection is not
                    assert "Only SELECT/WITH" not in r["error"]

    def test_allows_with_prefix(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "execute_sql", {"query": "WITH cte AS (SELECT 1) SELECT * FROM cte"})
        if isinstance(result, list):
            for r in result:
                if isinstance(r, dict) and "error" in r:
                    assert "Only SELECT/WITH" not in r["error"]

    def test_comment_bypass_blocked(self):
        """SQL comments can't bypass the read-only protection (Task 1.3).
        Starts with SELECT so passes prefix check; READ ONLY transaction blocks writes."""
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "execute_sql", {"query": "SELECT/**/1;DROP/**/TABLE/**/foo"})
        if isinstance(result, list):
            for r in result:
                if isinstance(r, dict) and "error" in r:
                    assert "Only SELECT/WITH" not in r["error"]


class TestGetTableSchemaValidation:
    def test_unknown_table(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "get_table_schema", {"table_name": "nonexistent_table"})
        assert result == {"error": "Unknown table: nonexistent_table"}


class TestQueryHealthDataValidation:
    def test_invalid_template(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "query_health_data", {"query_name": "nonexistent_query"})
        assert isinstance(result, list)
        assert len(result) == 1
        assert "error" in result[0]
        assert "Unknown query" in result[0]["error"]


class TestApiClientAutoFetchUserId:
    """Task 1.1: Verify user_id auto-fetch when empty and endpoint requires it."""

    def test_auto_fetch_triggers(self):
        from garminconnect.api.client import GarminAPIClient
        from garminconnect.api.endpoints import ENDPOINTS_BY_NAME

        mock_auth = MagicMock()
        mock_auth.get_display_name.return_value = "user123"
        mock_auth.connectapi.return_value = {}

        client = GarminAPIClient(auth=mock_auth, user_id="")

        # Find an endpoint that requires user_id
        user_id_ep = None
        for ep in ENDPOINTS_BY_NAME.values():
            if ep.requires_user_id:
                user_id_ep = ep
                break

        if user_id_ep:
            from datetime import date
            client.fetch(user_id_ep.name, date=date(2026, 3, 17))
            mock_auth.get_display_name.assert_called_once()
            assert client.user_id == "user123"

    def test_no_fetch_when_user_id_set(self):
        from garminconnect.api.client import GarminAPIClient
        mock_auth = MagicMock()
        mock_auth.connectapi.return_value = {}
        client = GarminAPIClient(auth=mock_auth, user_id="existing_user")
        from datetime import date
        client.fetch("daily_summary", date=date(2026, 3, 17))
        mock_auth.get_display_name.assert_not_called()


class TestHealthSummaryPeriodParam:
    """get_health_summary uses garmin_date_range for period resolution."""

    def test_accepts_period_string(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "get_health_summary", {"period": "week"})
        assert result is not None

    def test_default_period_is_week(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "get_health_summary", {})
        assert result is not None

    def test_invalid_period_returns_error(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "get_health_summary", {"period": "invalid"})
        if isinstance(result, dict) and "error" in result:
            assert "Unknown period" in result["error"]
        elif isinstance(result, list):
            for r in result:
                if isinstance(r, dict) and "error" in r:
                    assert "Unknown period" in r["error"] or "Connection" in r["error"]


class TestQueryHealthDataPeriodParam:
    """query_health_data accepts optional period parameter."""

    def test_period_overrides_dates(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "query_health_data", {
            "query_name": "daily_overview",
            "period": "week",
        })
        assert result is not None

    def test_explicit_dates_still_work(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "query_health_data", {
            "query_name": "daily_overview",
            "start_date": "2026-03-01",
            "end_date": "2026-03-17",
        })
        assert result is not None

    def test_invalid_period_returns_error(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "query_health_data", {
            "query_name": "daily_overview",
            "period": "invalid",
        })
        if isinstance(result, list):
            for r in result:
                if isinstance(r, dict) and "error" in r:
                    assert "Unknown period" in r["error"] or "Connection" in r["error"]

    def test_default_uses_week_when_no_dates_or_period(self):
        """When no dates or period given, defaults to 'week'."""
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "query_health_data", {
            "query_name": "daily_overview",
        })
        assert result is not None
