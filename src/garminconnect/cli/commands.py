from __future__ import annotations

import logging
from datetime import date, timedelta

import click
import structlog

from garminconnect.config import settings

logger = structlog.get_logger()


@click.group()
def cli() -> None:
    """Garmin Connect data server."""
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )


@cli.command()
@click.option("--days", default=30, help="Number of days to backfill")
@click.option("--force", is_flag=True, help="Re-sync already completed dates")
def backfill(days: int, force: bool) -> None:
    """Backfill historical data from Garmin Connect."""
    import sys

    from garminconnect.auth.client import GarminAuth
    from garminconnect.api.client import GarminAPIClient
    from garminconnect.db import create_engine_and_tables, get_mongo_db, HealthRepository
    from garminconnect.sync.pipeline import SyncPipeline

    auth = GarminAuth(token_dir=settings.garmin_token_dir)
    try:
        auth.ensure_authenticated(settings.garmin_email, settings.garmin_password)
    except Exception as e:
        click.echo(f"Authentication failed: {e}", err=True)
        click.echo(
            "Run 'docker compose run --rm garmin-cli login' first to authenticate.",
            err=True,
        )
        sys.exit(1)
    _, session_factory = create_engine_and_tables()
    mongo_db = get_mongo_db()
    repo = HealthRepository(session_factory=session_factory, mongo_db=mongo_db)
    api = GarminAPIClient(auth=auth)
    pipeline = SyncPipeline(api_client=api, repository=repo)
    end = date.today()
    start = end - timedelta(days=days)
    click.echo(f"Backfilling {days} days: {start} to {end}")
    pipeline.sync_range(start, end, force=force)
    click.echo("Syncing body composition...")
    pipeline.sync_body_composition(start, end)
    click.echo("Syncing activities (with trackpoints)...")
    synced_ids = pipeline.sync_activities(limit=100)
    click.echo(f"Synced {len(synced_ids)} activities.")
    click.echo("Syncing endurance score...")
    pipeline.sync_endurance_score()
    click.echo("Syncing hill score...")
    pipeline.sync_hill_score()
    click.echo("Syncing workouts...")
    pipeline.sync_workouts()
    click.echo("Syncing personal records...")
    pipeline.sync_personal_records()
    click.echo("Syncing badges...")
    pipeline.sync_badges()
    click.echo("Syncing lactate threshold...")
    pipeline.sync_lactate_threshold()
    click.echo("Syncing cycling FTP...")
    pipeline.sync_cycling_ftp()
    click.echo("Syncing gear...")
    pipeline.sync_gear()
    click.echo("Syncing hydration...")
    current = start
    while current <= end:
        pipeline.sync_hydration(current)
        current += timedelta(days=1)
    click.echo("Syncing calendar...")
    pipeline.sync_calendar()
    click.echo("Backfill complete.")


@cli.command()
def daemon() -> None:
    """Start the polling daemon."""
    import sys

    from garminconnect.auth.client import GarminAuth
    from garminconnect.api.client import GarminAPIClient
    from garminconnect.db import create_engine_and_tables, get_mongo_db, HealthRepository
    from garminconnect.sync.pipeline import SyncPipeline
    from garminconnect.sync.scheduler import GarminScheduler

    auth = GarminAuth(token_dir=settings.garmin_token_dir)
    try:
        auth.ensure_authenticated(settings.garmin_email, settings.garmin_password)
    except Exception as e:
        click.echo(f"Authentication failed: {e}", err=True)
        click.echo(
            "Run 'docker compose run --rm garmin-cli login' first to authenticate.",
            err=True,
        )
        sys.exit(1)
    _, session_factory = create_engine_and_tables()
    mongo_db = get_mongo_db()
    repo = HealthRepository(session_factory=session_factory, mongo_db=mongo_db)
    api = GarminAPIClient(auth=auth)
    pipeline = SyncPipeline(api_client=api, repository=repo)
    scheduler = GarminScheduler(pipeline=pipeline, interval_minutes=settings.poll_interval_minutes)
    click.echo(f"Starting daemon (polling every {settings.poll_interval_minutes} min)...")
    scheduler.start()


@cli.command()
def mcp() -> None:
    """Start the MCP server."""
    from garminconnect.mcp.server import create_mcp_server, BearerAuthMiddleware

    server = create_mcp_server(
        postgres_url=settings.postgres_url,
        api_key=settings.mcp_api_key,
        garth_token_dir=settings.garmin_token_dir,
    )
    transport = settings.mcp_transport
    if transport == "sse":
        click.echo(f"Starting MCP server (SSE) on {settings.mcp_host}:{settings.mcp_port}...")
        if settings.mcp_api_key:
            click.echo("Bearer token authentication enabled.")
        else:
            click.echo("WARNING: No MCP_API_KEY set — authentication disabled.")
        # Build the ASGI app with auth middleware wrapping it
        import uvicorn
        from starlette.middleware import Middleware
        middleware = []
        if settings.mcp_api_key:
            middleware.append(Middleware(BearerAuthMiddleware, api_key=settings.mcp_api_key))
        app = server.http_app(transport="sse", middleware=middleware)
        uvicorn.run(app, host=settings.mcp_host, port=settings.mcp_port)
    elif transport == "streamable-http":
        click.echo(f"Starting MCP server (HTTP) on {settings.mcp_host}:{settings.mcp_port}...")
        if settings.mcp_api_key:
            click.echo("Bearer token authentication enabled.")
        else:
            click.echo("WARNING: No MCP_API_KEY set — authentication disabled.")
        import uvicorn
        from starlette.middleware import Middleware
        middleware = []
        if settings.mcp_api_key:
            middleware.append(Middleware(BearerAuthMiddleware, api_key=settings.mcp_api_key))
        app = server.http_app(transport="streamable-http", path="/", middleware=middleware)
        uvicorn.run(app, host=settings.mcp_host, port=settings.mcp_port)
    else:
        click.echo("Starting MCP server (stdio)...")
        server.run(transport="stdio")


@cli.command()
def login() -> None:
    """Authenticate with Garmin Connect and store tokens."""
    import sys

    from garminconnect.auth.client import GarminAuth

    email = settings.garmin_email
    password = settings.garmin_password

    if not email or not password or email == "your@email.com":
        click.echo("No credentials found in .env — prompting interactively.")
        email = click.prompt("Garmin email")
        password = click.prompt("Garmin password", hide_input=True)

    auth = GarminAuth(token_dir=settings.garmin_token_dir)
    try:
        auth.login(email, password)
        click.echo(f"Logged in. Tokens saved to {settings.garmin_token_dir}")
    except Exception as e:
        click.echo(f"Login failed: {e}", err=True)
        sys.exit(1)


@cli.command("sync-one")
@click.option("--endpoint", required=True, help="Endpoint name (e.g., daily_summary, heart_rate, stress)")
@click.option("--date", "target_date", required=True, help="Date to sync (YYYY-MM-DD)")
@click.option("--force", is_flag=True, help="Re-sync even if already completed")
def sync_one(endpoint: str, target_date: str, force: bool) -> None:
    """Sync a single endpoint for a single date."""
    import sys

    from garminconnect.auth.client import GarminAuth
    from garminconnect.api.client import GarminAPIClient
    from garminconnect.db import create_engine_and_tables, get_mongo_db, HealthRepository
    from garminconnect.sync.pipeline import SyncPipeline, DAILY_SYNC_ENDPOINTS

    # Validate endpoint name
    valid_endpoints = list(DAILY_SYNC_ENDPOINTS) + [
        "body_composition", "weight", "activities",
        "workouts", "personal_records", "badges", "calendar",
        "race_predictions", "endurance_score", "hill_score",
        "lactate_threshold", "cycling_ftp", "hydration", "gear",
    ]
    if endpoint not in valid_endpoints:
        click.echo(f"Unknown endpoint: {endpoint}", err=True)
        click.echo(f"Valid endpoints: {', '.join(valid_endpoints)}", err=True)
        sys.exit(1)

    # Parse the date
    try:
        parsed_date = date.fromisoformat(target_date)
    except ValueError:
        click.echo(f"Invalid date format: {target_date}. Use YYYY-MM-DD.", err=True)
        sys.exit(1)

    # Authenticate
    auth = GarminAuth(token_dir=settings.garmin_token_dir)
    try:
        auth.ensure_authenticated(settings.garmin_email, settings.garmin_password)
    except Exception as e:
        click.echo(f"Authentication failed: {e}", err=True)
        click.echo(
            "Run 'docker compose run --rm garmin-cli login' first to authenticate.",
            err=True,
        )
        sys.exit(1)

    # Set up pipeline
    _, session_factory = create_engine_and_tables()
    mongo_db = get_mongo_db()
    repo = HealthRepository(session_factory=session_factory, mongo_db=mongo_db)
    api = GarminAPIClient(auth=auth)
    pipeline = SyncPipeline(api_client=api, repository=repo)

    # Sync
    click.echo(f"Syncing {endpoint} for {parsed_date}...")
    if endpoint == "activities":
        synced = pipeline.sync_activities(limit=20)
        click.echo(f"Synced {len(synced)} activities.")
    elif endpoint in ("body_composition", "weight"):
        count = pipeline.sync_body_composition(parsed_date, parsed_date)
        click.echo(f"Synced {count} body composition entries.")
    elif endpoint == "workouts":
        synced = pipeline.sync_workouts()
        click.echo(f"Synced {len(synced)} workouts.")
    elif endpoint == "personal_records":
        count = pipeline.sync_personal_records()
        click.echo(f"Synced {count} personal records.")
    elif endpoint == "badges":
        count = pipeline.sync_badges()
        click.echo(f"Synced {count} badges.")
    elif endpoint == "calendar":
        count = pipeline.sync_calendar(year=parsed_date.year, month=parsed_date.month)
        click.echo(f"Synced {count} calendar items for {parsed_date.year}-{parsed_date.month:02d}.")
    elif endpoint == "race_predictions":
        pipeline.sync_race_predictions()
        click.echo("Synced race predictions.")
    elif endpoint == "endurance_score":
        pipeline.sync_endurance_score()
        click.echo("Synced endurance score.")
    elif endpoint == "hill_score":
        pipeline.sync_hill_score()
        click.echo("Synced hill score.")
    elif endpoint == "lactate_threshold":
        count = pipeline.sync_lactate_threshold()
        click.echo(f"Synced {count} lactate threshold entries.")
    elif endpoint == "cycling_ftp":
        pipeline.sync_cycling_ftp()
        click.echo("Synced cycling FTP.")
    elif endpoint == "hydration":
        pipeline.sync_hydration(parsed_date)
        click.echo(f"Synced hydration for {parsed_date}.")
    elif endpoint == "gear":
        count = pipeline.sync_gear()
        click.echo(f"Synced {count} gear items.")
    else:
        results = pipeline.sync_date(parsed_date, endpoints=[endpoint], force=force)
        status = results.get(endpoint, "unknown")
        if status == "completed":
            click.echo(f"Successfully synced {endpoint} for {parsed_date}.")
        elif status == "skipped":
            click.echo(f"Already synced {endpoint} for {parsed_date}. Use --force to re-sync.")
        else:
            click.echo(f"Failed to sync {endpoint} for {parsed_date}.", err=True)
            sys.exit(1)


@cli.command()
def status() -> None:
    """Show sync status."""
    from garminconnect.db import create_engine_and_tables
    from sqlalchemy import text

    engine, _ = create_engine_and_tables()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT metric_name, MAX(date) AS last_date, "
                "COUNT(*) FILTER (WHERE status = 'completed') AS ok, "
                "COUNT(*) FILTER (WHERE status = 'failed') AS fail "
                "FROM sync_status GROUP BY metric_name ORDER BY metric_name"
            )
        ).fetchall()
        for row in rows:
            click.echo(f"  {row[0]:25s} last={row[1]}  ok={row[2]}  fail={row[3]}")
