# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

garminconnectconnect — a self-hosted Garmin Connect data server that polls Garmin Connect, stores data in TimescaleDB (processed) and MongoDB (raw), exposes it via MCP server for AI querying, and visualizes with Grafana. Everything runs in Docker.

## Tech Stack

- Python 3.12+, SQLAlchemy 2.0, garth (Garmin auth), PyMongo, FastMCP, Click, APScheduler
- PostgreSQL 16 + TimescaleDB (time-series data)
- MongoDB 7 (raw JSON archival)
- Grafana (dashboards)
- Docker Compose (all services)

## Commands

```bash
# Run unit tests
pytest tests/ --ignore=tests/test_integration.py -v

# Run integration tests (needs Docker)
pytest tests/test_integration.py -v

# Build Docker image
docker compose build

# Start everything
docker compose up -d

# CLI commands
docker compose run --rm garmin-cli login
docker compose run --rm garmin-cli backfill --days 30
docker compose run --rm garmin-cli status
```

## Architecture

- `src/garminconnect/auth/` — garth-based Garmin Connect authentication
- `src/garminconnect/api/` — API client with 30 endpoint definitions, rate limiting
- `src/garminconnect/models/` — SQLAlchemy models for 16 tables (daily, monitoring, sleep, activities, training)
- `src/garminconnect/db/` — TimescaleDB + MongoDB connection and repository pattern
- `src/garminconnect/sync/` — extractors (JSON->models), sync pipeline, APScheduler daemon
- `src/garminconnect/mcp/` — FastMCP server with 6 tools for AI querying
- `src/garminconnect/cli/` — Click CLI (login, backfill, daemon, mcp, status)
- `grafana/` — Auto-provisioned datasource and 15-panel health dashboard

## Key Design Decisions

- **Dual database**: TimescaleDB for queryable processed data, MongoDB for raw JSON archival (future reprocessing)
- **garth for auth**: Community-maintained OAuth library, more reliable than self-rolled SSO
- **Hypertables**: HR, stress, body battery, SpO2, respiration, sleep stages use TimescaleDB hypertables for time-series performance
- **Idempotent sync**: sync_status table tracks what's been synced per metric per date, prevents re-fetching
- **Rate limiting**: 1 second minimum between API calls, 10-minute polling interval (safe for Garmin's undocumented limits)
