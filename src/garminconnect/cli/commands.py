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
    click.echo("Syncing activities...")
    pipeline.sync_activities(limit=100)
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
    from garminconnect.mcp.server import create_mcp_server

    server = create_mcp_server(postgres_url=settings.postgres_url)
    click.echo("Starting MCP server...")
    server.run(transport=settings.mcp_transport)


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
