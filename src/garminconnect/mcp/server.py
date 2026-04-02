from __future__ import annotations
import re
from datetime import date, timedelta
from typing import Any
from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from sqlalchemy import create_engine, text
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from garminconnect.mcp.tools import QUERY_TEMPLATES, get_table_list


class BearerAuthMiddleware:
    """ASGI middleware that validates Bearer token authentication."""

    def __init__(self, app: ASGIApp, api_key: str = "") -> None:
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        if scope["type"] not in ("http", "websocket") or not self.api_key:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()

        if auth_header == f"Bearer {self.api_key}":
            await self.app(scope, receive, send)
            return

        # Return 401 for HTTP requests
        if scope["type"] == "http":
            response = JSONResponse(
                {"error": "Unauthorized", "detail": "Valid Bearer token required"},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        # For websocket, just close
        await send({"type": "websocket.close", "code": 4001})


_WRITE_KEYWORDS = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY)\b',
    re.IGNORECASE,
)


def create_mcp_server(postgres_url: str, api_key: str = "", garth_token_dir: str = "") -> FastMCP:
    mcp = FastMCP("Garmin Health Data")
    mcp._auth_api_key = api_key
    if postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(postgres_url, pool_pre_ping=True)
    ro_engine = create_engine(postgres_url, pool_pre_ping=True,
                              execution_options={"postgresql_readonly": True})
    _RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

    @mcp.tool(annotations=_RO)
    def list_tables() -> dict[str, Any]:
        """List all available health data tables and their row counts."""
        _valid_tables = set(get_table_list())
        result = {}
        with engine.connect() as conn:
            for table in get_table_list():
                if table not in _valid_tables:
                    continue
                try:
                    row = conn.execute(
                        text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = :t"),
                        {"t": table},
                    ).fetchone()
                    if row and row[0] > 0:
                        count_row = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                        result[table] = count_row[0] if count_row else 0
                    else:
                        result[table] = "table not found"
                except Exception:
                    result[table] = "table not found"
        return result

    @mcp.tool(annotations=_RO)
    def get_table_schema(table_name: str = "") -> dict[str, Any]:
        """Get column names and types for a specific table.

        Args:
            table_name: Name of the table to inspect (required).
        """
        if not table_name:
            return {"error": "table_name is required", "available_tables": get_table_list()}
        if table_name not in get_table_list():
            return {"error": f"Unknown table: {table_name}"}
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = :table ORDER BY ordinal_position"),
                {"table": table_name},
            ).fetchall()
            return {row[0]: row[1] for row in rows}

    @mcp.tool(annotations=_RO)
    def query_health_data(query_name: str, start_date: str = "", end_date: str = "", period: str = "", limit: int = 30) -> list[dict]:
        """Run a pre-built health data query.

        Available: daily_overview, sleep_trend, hr_intraday, activity_list,
        training_readiness_trend, hrv_trend, body_composition_trend, stress_intraday,
        weekly_comparison, activity_detail, personal_records, recovery_analysis.

        Args:
            query_name: Name of the query template.
            start_date: Explicit start (YYYY-MM-DD). Ignored if period is set.
            end_date: Explicit end (YYYY-MM-DD). Ignored if period is set.
            period: Garmin-aligned period — "week", "4weeks", "month",
                    "month-1", "year", or a number like "30". Overrides
                    start_date/end_date.
            limit: Max rows for activity_list (default 30).
        """
        template = QUERY_TEMPLATES.get(query_name)
        if not template:
            return [{"error": f"Unknown query. Available: {list(QUERY_TEMPLATES.keys())}"}]

        if period:
            from garminconnect.utils.date_ranges import garmin_date_range
            try:
                start, end = garmin_date_range(period)
            except ValueError as e:
                return [{"error": str(e)}]
        else:
            end = date.fromisoformat(end_date) if end_date else date.today() - timedelta(days=1)
            start = date.fromisoformat(start_date) if start_date else end - timedelta(days=6)

        with engine.connect() as conn:
            result = conn.execute(text(template), {"start": start.isoformat(), "end": end.isoformat(), "limit": limit})
            return [dict(row._mapping) for row in result.fetchall()]

    @mcp.tool(annotations=_RO)
    def execute_sql(query: str) -> list[dict]:
        """Execute a read-only SQL query. Only SELECT statements allowed."""
        normalized = query.strip().upper()
        if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
            return [{"error": "Only SELECT/WITH queries are allowed"}]
        if _WRITE_KEYWORDS.search(normalized):
            return [{"error": "Write operations (INSERT/UPDATE/DELETE/DROP/etc.) are not allowed"}]
        with ro_engine.connect() as conn:
            try:
                result = conn.execute(text(query))
                rows = result.fetchmany(500)
                return [dict(row._mapping) for row in rows]
            except Exception as e:
                return [{"error": f"Query failed: {e}"}]

    @mcp.tool(annotations=_RO)
    def get_health_summary(period: str = "week") -> dict[str, Any]:
        """Get a comprehensive health summary for a Garmin-aligned period.

        Args:
            period: "week", "4weeks", "month", "month-1", "year", or a
                    number like "30" for arbitrary day counts. Periods use
                    Garmin's Monday-to-Sunday week convention and exclude
                    today (partial day).
        """
        from garminconnect.utils.date_ranges import garmin_date_range

        try:
            start, end = garmin_date_range(period)
        except ValueError as e:
            return {"error": str(e)}

        summary: dict[str, Any] = {"period": {"start": start.isoformat(), "end": end.isoformat()}}
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
                "SUM(calories) AS total_calories FROM activities WHERE start_time >= :s AND start_time < :e"
            ), {"s": start.isoformat(), "e": (end + timedelta(days=1)).isoformat()}).fetchone()
            if row:
                summary["activities"] = dict(row._mapping)
        return summary

    @mcp.tool(annotations=_RO)
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

    @mcp.tool(annotations=_RO)
    def compare_activities(activity_ids: str) -> dict[str, Any]:
        """WHEN TO USE: Compare 2-5 activities side by side. Pass comma-separated activity IDs.

        Args:
            activity_ids: Comma-separated activity IDs (e.g., "123,456,789"). Min 2, max 5.
        """
        ids = [aid.strip() for aid in activity_ids.split(",") if aid.strip()]
        if len(ids) < 2:
            return {"error": "Provide at least 2 activity IDs (comma-separated)"}
        if len(ids) > 5:
            return {"error": "Provide at most 5 activity IDs"}
        placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
        params = {f"id{i}": aid for i, aid in enumerate(ids)}
        with engine.connect() as conn:
            rows = conn.execute(text(
                f"SELECT activity_id, name, activity_type, start_time, "
                f"duration_seconds, distance_meters, avg_heart_rate, max_heart_rate, "
                f"avg_speed, calories, elevation_gain, avg_cadence, "
                f"training_effect_aerobic, training_load, vo2max, "
                f"avg_ground_contact_time, avg_stride_length "
                f"FROM activities WHERE activity_id IN ({placeholders}) "
                f"ORDER BY start_time"
            ), params).fetchall()
            if not rows:
                return {"error": "No activities found for the given IDs"}
            activities = [dict(row._mapping) for row in rows]
            insights = []
            hrs = [a["avg_heart_rate"] for a in activities if a.get("avg_heart_rate")]
            if hrs:
                insights.append(f"HR range: {min(hrs)}-{max(hrs)} bpm")
            dists = [a["distance_meters"] for a in activities if a.get("distance_meters")]
            if dists:
                insights.append(f"Distance range: {min(dists)/1000:.1f}-{max(dists)/1000:.1f} km")
            return {"activities": activities, "insights": insights, "count": len(activities)}

    @mcp.tool(annotations=_RO)
    def find_similar_activities(activity_id: str, tolerance_pct: int = 20, limit: int = 10) -> list[dict]:
        """WHEN TO USE: Find activities similar to a reference activity by type, distance, and duration.

        Args:
            activity_id: Reference activity ID.
            tolerance_pct: How similar (default 20 = within 20% of distance/duration).
            limit: Max results (default 10).
        """
        with engine.connect() as conn:
            ref = conn.execute(text(
                "SELECT activity_type, distance_meters, duration_seconds "
                "FROM activities WHERE activity_id = :id"
            ), {"id": activity_id}).fetchone()
            if not ref:
                return [{"error": f"Activity {activity_id} not found"}]
            ref_map = dict(ref._mapping)
            factor = tolerance_pct / 100.0
            dist = ref_map.get("distance_meters") or 0
            dur = ref_map.get("duration_seconds") or 0
            rows = conn.execute(text(
                "SELECT activity_id, name, start_time, distance_meters, duration_seconds, "
                "avg_heart_rate, avg_speed, calories "
                "FROM activities "
                "WHERE activity_type = :atype AND activity_id != :id "
                "AND distance_meters BETWEEN :dlo AND :dhi "
                "AND duration_seconds BETWEEN :tlo AND :thi "
                "ORDER BY start_time DESC LIMIT :limit"
            ), {
                "atype": ref_map["activity_type"], "id": activity_id,
                "dlo": dist * (1 - factor), "dhi": dist * (1 + factor),
                "tlo": dur * (1 - factor), "thi": dur * (1 + factor),
                "limit": limit,
            }).fetchall()
            return [dict(row._mapping) for row in rows]

    import json as _json

    @mcp.resource("garmin://instructions", description="How to query Garmin health data")
    def query_instructions() -> str:
        return (
            "Garmin health data MCP server -- 28 tables in TimescaleDB.\n\n"
            "Tools:\n"
            "- list_tables: See tables and row counts\n"
            "- get_table_schema: Column details for any table\n"
            "- query_health_data: Pre-built queries (pass period='week','4weeks','month','year' or explicit dates)\n"
            "- execute_sql: Custom read-only SQL (SELECT/WITH only, max 500 rows)\n"
            "- get_health_summary: Quick overview of key metrics\n"
            "- get_sync_status: When each metric was last synced\n\n"
            "Dates: Weeks are Mon-Sun. Periods exclude today (partial day).\n"
            "Periods: 'week', '4weeks', 'month', 'month-1', 'year', or a number like '30'."
        )

    @mcp.resource("garmin://tables", description="All health data table names")
    def available_tables() -> str:
        return _json.dumps(get_table_list(), indent=2)

    @mcp.resource("garmin://queries", description="Available pre-built query template names")
    def available_queries() -> str:
        return _json.dumps(list(QUERY_TEMPLATES.keys()), indent=2)

    @mcp.prompt()
    def weekly_health_review(period: str = "week") -> str:
        """WHEN TO USE: When asked about overall health, weekly review, or general wellness status."""
        return (
            f"Analyze health data for period='{period}' using these tools:\n"
            f"1. get_health_summary(period='{period}') for daily averages\n"
            f"2. query_health_data('sleep_trend', period='{period}') for sleep\n"
            f"3. query_health_data('hrv_trend', period='{period}') for HRV\n"
            f"4. query_health_data('training_readiness_trend', period='{period}') for readiness\n"
            f"Synthesize into actionable insights about recovery, fitness, and sleep."
        )

    @mcp.prompt()
    def activity_analysis(activity_type: str = "running") -> str:
        """WHEN TO USE: When asked about recent activities, training progress, or performance trends."""
        return (
            f"Analyze recent {activity_type} activities:\n"
            f"1. query_health_data('activity_list', limit=10) for recent activities\n"
            f"2. execute_sql to filter by activity_type='{activity_type}'\n"
            f"Look for trends in pace, HR, training effect, and distance."
        )

    @mcp.prompt()
    def recovery_check() -> str:
        """WHEN TO USE: When asked if ready to train, about recovery, or readiness."""
        return (
            "Assess recovery and readiness:\n"
            "1. query_health_data('recovery_analysis', period='week')\n"
            "2. query_health_data('training_readiness_trend', period='week')\n"
            "3. query_health_data('sleep_trend', period='3')\n"
            "Recommend: train hard, easy recovery, or rest today."
        )

    @mcp.prompt()
    def sleep_report(period: str = "week") -> str:
        """WHEN TO USE: When asked about sleep quality, patterns, or sleep issues."""
        return (
            f"Analyze sleep for period='{period}':\n"
            f"1. query_health_data('sleep_trend', period='{period}')\n"
            f"2. query_health_data('hrv_trend', period='{period}') for overnight HRV\n"
            f"Evaluate: duration consistency, deep/REM ratios, sleep score trends, HRV correlation."
        )

    @mcp.prompt()
    def training_deep_dive(period: str = "4weeks") -> str:
        """WHEN TO USE: When asked about training load, status, VO2max, or fitness trends."""
        return (
            f"Deep training analysis for period='{period}':\n"
            f"1. query_health_data('training_status_trend', period='{period}')\n"
            f"2. query_health_data('activity_list', period='{period}')\n"
            f"3. query_health_data('race_predictions_trend', period='{period}')\n"
            f"4. query_health_data('endurance_hill_scores', period='{period}')\n"
            f"Analyze: training status progression, weekly load, VO2max trend, race prediction changes."
        )

    @mcp.prompt()
    def compare_recent_runs() -> str:
        """WHEN TO USE: When asked to compare runs or track running improvement."""
        return (
            "Compare recent running activities:\n"
            "1. execute_sql: SELECT activity_id, name, start_time, distance_meters/1000 AS km, "
            "duration_seconds/60 AS mins, avg_heart_rate, avg_speed, avg_cadence, "
            "avg_ground_contact_time, avg_stride_length, training_load "
            "FROM activities WHERE activity_type='running' ORDER BY start_time DESC LIMIT 10\n"
            "2. Compare pace, HR efficiency (pace/HR), running dynamics, training load.\n"
            "3. Highlight improvements and areas to work on."
        )

    # --- Workout write-back tools (require garth_token_dir) ---

    import garth as _garth
    from garminconnect.mcp.workout_builder import build_workout_payload

    _WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
    _DELETE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True)

    def _garth_write(path: str, method: str = "POST", json_data: dict | None = None) -> Any:
        """Call Garmin API with write capability via garth."""
        if not garth_token_dir:
            raise ValueError("Workout write-back not configured (no garth_token_dir)")
        _garth.resume(garth_token_dir)
        return _garth.connectapi(path, method=method, json=json_data)

    @mcp.tool(annotations=_WRITE)
    def create_workout(name: str, sport: str = "running", steps_json: str = "[]") -> dict[str, Any]:
        """Create a workout on Garmin Connect.

        Args:
            name: Workout name.
            sport: Sport type (running, cycling, swimming, strength).
            steps_json: JSON array of step objects. Each step: {"type": "warmup|interval|cooldown|recovery|rest",
                        "duration_seconds": int, "distance_meters": float, "target_pace_min": [slow, fast],
                        "description": str}
        """
        if not garth_token_dir:
            return {"error": "Workout write-back not configured (no garth_token_dir)"}
        steps = _json.loads(steps_json)
        payload = build_workout_payload(name, sport, steps)
        result = _garth_write("/workout-service/workout", method="POST", json_data=payload)
        return {"success": True, "workout": result}

    @mcp.tool(annotations=_WRITE)
    def schedule_workout(workout_id: str, target_date: str = "") -> dict[str, Any]:
        """Schedule a workout on a specific date.

        Args:
            workout_id: Garmin workout ID.
            target_date: Date in YYYY-MM-DD format. Defaults to tomorrow.
        """
        if not garth_token_dir:
            return {"error": "Workout write-back not configured"}
        if not target_date:
            from datetime import date as _date, timedelta as _td
            target_date = (_date.today() + _td(days=1)).isoformat()
        result = _garth_write(
            f"/workout-service/schedule/{workout_id}",
            method="POST",
            json_data={"date": target_date},
        )
        return {"success": True, "scheduled": result}

    @mcp.tool(annotations=_DELETE)
    def delete_workout(workout_id: str) -> dict[str, Any]:
        """Delete a workout from Garmin Connect. This is irreversible.

        Args:
            workout_id: Garmin workout ID to delete.
        """
        if not garth_token_dir:
            return {"error": "Workout write-back not configured"}
        _garth_write(f"/workout-service/workout/{workout_id}", method="DELETE")
        return {"success": True, "deleted": workout_id}

    return mcp
