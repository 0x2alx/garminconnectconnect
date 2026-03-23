"""Tests for MCP prompt templates."""
import asyncio
import pytest
from garminconnect.mcp.server import create_mcp_server

EXPECTED_PROMPTS = [
    "weekly_health_review",
    "activity_analysis",
    "recovery_check",
    "sleep_report",
    "training_deep_dive",
    "compare_recent_runs",
]


@pytest.fixture
def mcp():
    return create_mcp_server("postgresql+psycopg://fake:fake@localhost/fake")


def test_all_prompts_registered(mcp):
    loop = asyncio.new_event_loop()
    try:
        prompts = loop.run_until_complete(mcp.list_prompts())
        prompt_names = [p.name for p in prompts]
        for name in EXPECTED_PROMPTS:
            assert name in prompt_names, f"Missing prompt: {name}"
    finally:
        loop.close()


def test_weekly_health_review_renders(mcp):
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(mcp.render_prompt("weekly_health_review", {"period": "week"}))
        # render_prompt returns a PromptResult with .messages
        text = result.messages[0].content.text
        assert "get_health_summary" in text
    finally:
        loop.close()


def test_activity_analysis_renders(mcp):
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(mcp.render_prompt("activity_analysis", {"activity_type": "cycling"}))
        text = result.messages[0].content.text
        assert "cycling" in text
    finally:
        loop.close()


def test_recovery_check_renders(mcp):
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(mcp.render_prompt("recovery_check", {}))
        text = result.messages[0].content.text
        assert "recovery_analysis" in text
    finally:
        loop.close()


def test_sleep_report_renders(mcp):
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(mcp.render_prompt("sleep_report", {"period": "week"}))
        text = result.messages[0].content.text
        assert "sleep_trend" in text
    finally:
        loop.close()


def test_training_deep_dive_renders(mcp):
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(mcp.render_prompt("training_deep_dive", {"period": "4weeks"}))
        text = result.messages[0].content.text
        assert "training_status_trend" in text
    finally:
        loop.close()


def test_compare_recent_runs_renders(mcp):
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(mcp.render_prompt("compare_recent_runs", {}))
        text = result.messages[0].content.text
        assert "running" in text
    finally:
        loop.close()
