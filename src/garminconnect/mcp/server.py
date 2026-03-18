from __future__ import annotations
from datetime import date, timedelta
from typing import Any
from fastmcp import FastMCP
from sqlalchemy import create_engine, text
from garminconnect.mcp.tools import QUERY_TEMPLATES, get_table_list


def create_mcp_server(postgres_url: str) -> FastMCP:
    mcp = FastMCP("Garmin Health Data")
    engine = create_engine(postgres_url, pool_pre_ping=True)

    @mcp.tool()
    def list_tables() -> dict[str, Any]:
        """List all available health data tables and their row counts."""
        result = {}
        with engine.connect() as conn:
            for table in get_table_list():
                try:
                    row = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                    result[table] = row[0] if row else 0
                except Exception:
                    result[table] = "table not found"
        return result

    @mcp.tool()
    def get_table_schema(table_name: str) -> dict[str, Any]:
        """Get column names and types for a specific table."""
        if table_name not in get_table_list():
            return {"error": f"Unknown table: {table_name}"}
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = :table ORDER BY ordinal_position"),
                {"table": table_name},
            ).fetchall()
            return {row[0]: row[1] for row in rows}

    @mcp.tool()
    def query_health_data(query_name: str, start_date: str = "", end_date: str = "", limit: int = 30) -> list[dict]:
        """Run a pre-built health data query. Available: daily_overview, sleep_trend, hr_intraday, activity_list, training_readiness_trend, hrv_trend, body_composition_trend, stress_intraday."""
        template = QUERY_TEMPLATES.get(query_name)
        if not template:
            return [{"error": f"Unknown query. Available: {list(QUERY_TEMPLATES.keys())}"}]
        end = date.fromisoformat(end_date) if end_date else date.today()
        start = date.fromisoformat(start_date) if start_date else end - timedelta(days=7)
        with engine.connect() as conn:
            result = conn.execute(text(template), {"start": start.isoformat(), "end": end.isoformat(), "limit": limit})
            return [dict(row._mapping) for row in result.fetchall()]

    @mcp.tool()
    def execute_sql(query: str) -> list[dict]:
        """Execute a read-only SQL query. Only SELECT/WITH allowed."""
        normalized = query.strip().upper()
        if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
            return [{"error": "Only SELECT/WITH queries are allowed"}]
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            try:
                result = conn.execute(text(query))
                rows = result.fetchmany(500)
                return [dict(row._mapping) for row in rows]
            except Exception as e:
                return [{"error": f"Query failed: {e}"}]

    @mcp.tool()
    def get_health_summary(days: int = 7) -> dict[str, Any]:
        """Get a comprehensive health summary for the last N days."""
        end = date.today()
        start = end - timedelta(days=days)
        summary: dict[str, Any] = {}
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT AVG(total_steps) AS avg_steps, AVG(total_calories) AS avg_calories, "
                "AVG(resting_heart_rate) AS avg_rhr, AVG(avg_stress) AS avg_stress, "
                "AVG(avg_spo2) AS avg_spo2 FROM daily_summary WHERE date BETWEEN :s AND :e"
            ), {"s": start.isoformat(), "e": end.isoformat()}).fetchone()
            if row:
                summary["daily_averages"] = dict(row._mapping)
            row = conn.execute(text(
                "SELECT AVG(total_sleep_seconds)/3600.0 AS avg_sleep_hours, "
                "AVG(sleep_score) AS avg_sleep_score FROM sleep_summary WHERE date BETWEEN :s AND :e"
            ), {"s": start.isoformat(), "e": end.isoformat()}).fetchone()
            if row:
                summary["sleep_averages"] = dict(row._mapping)
            row = conn.execute(text(
                "SELECT COUNT(*) AS count, SUM(distance_meters)/1000.0 AS total_km, "
                "SUM(calories) AS total_calories FROM activities WHERE start_time >= :s"
            ), {"s": start.isoformat()}).fetchone()
            if row:
                summary["activities"] = dict(row._mapping)
        return summary

    @mcp.tool()
    def get_sync_status() -> list[dict]:
        """Check the sync status - when was each metric last synced?"""
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT metric_name, MAX(date) AS last_date, "
                "COUNT(*) FILTER (WHERE status = 'completed') AS completed, "
                "COUNT(*) FILTER (WHERE status = 'failed') AS failed "
                "FROM sync_status GROUP BY metric_name ORDER BY metric_name"
            )).fetchall()
            return [dict(zip(["metric", "last_date", "completed", "failed"], row)) for row in rows]

    return mcp
