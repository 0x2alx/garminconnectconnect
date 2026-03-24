# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

garminconnectconnect — a self-hosted Garmin Connect data server that polls Garmin Connect, stores data in TimescaleDB (processed) and MongoDB (raw), and exposes it via MCP server for AI querying. Everything runs in Docker.

## Tech Stack

- Python 3.12+, SQLAlchemy 2.0, garth (Garmin auth), PyMongo, FastMCP, Click, APScheduler
- PostgreSQL 16 + TimescaleDB (time-series data)
- MongoDB 7 (raw JSON archival)
- Docker Compose (all services)

## Commands

```bash
# Run unit tests
pytest tests/ --ignore=tests/test_integration.py -v

# Run a single test file
pytest tests/test_extractors.py -v

# Run a single test by name
pytest tests/test_extractors.py -k "test_extract_heart_rate" -v

# Run integration tests (needs Docker — uses testcontainers for real DB instances)
pytest tests/test_integration.py -v

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Build and run — ALWAYS use --no-cache after code changes to avoid stale wheel cache
docker compose build --no-cache
docker compose up -d

# CLI commands (garmin-cli profile runs interactively, not as a daemon)
docker compose run --rm garmin-cli login
docker compose run --rm garmin-cli backfill --days 30
docker compose run --rm garmin-cli sync-one --endpoint heart_rate --date 2025-01-15
docker compose run --rm garmin-cli status
```

## Architecture

- `src/garminconnect/config.py` — Pydantic Settings class, all config via env vars (30+), see `.env.example`
- `src/garminconnect/auth/` — garth-based Garmin Connect authentication, token auto-refresh
- `src/garminconnect/api/` — API client with 43 endpoint definitions, rate limiting (1 req/sec), URL templating with `{date}`, `{user_id}`, `{activity_id}` placeholders
- `src/garminconnect/models/` — SQLAlchemy models for 34 tables (daily, monitoring, sleep, activities, training, workouts, gamification, biometrics, gear, hydration)
- `src/garminconnect/db/` — TimescaleDB + MongoDB connection and HealthRepository pattern (unified interface for both DBs)
- `src/garminconnect/sync/` — extractors (JSON→models), sync pipeline (fetch→store raw→extract→upsert), APScheduler daemon
- `src/garminconnect/mcp/` — FastMCP server with 11 tools (8 read-only + 3 workout write-back), 6 prompts, 3 resources, 37 query templates, BearerAuthMiddleware, read-only SQL enforcement via regex
- `src/garminconnect/cli/` — Click CLI (login, backfill, sync-one, daemon, mcp, status). Uses lazy imports per command.
- `src/garminconnect/utils/` — Garmin-aligned date range calculations (Monday–Sunday weeks, "today" excluded)
- `alembic/` — Database migrations; env.py handles TimescaleDB hypertable creation

## Key Design Decisions

- **Dual database**: TimescaleDB for queryable processed data, MongoDB for raw JSON archival (future reprocessing)
- **garth for auth**: Community-maintained OAuth library, more reliable than self-rolled SSO
- **Hypertables**: HR, stress, body battery, SpO2, respiration, sleep stages, activity trackpoints, HRV readings use TimescaleDB hypertables for time-series performance
- **Idempotent sync**: sync_status table tracks what's been synced per metric per date, prevents re-fetching
- **Rate limiting**: 1 second minimum between API calls, 10-minute polling interval (safe for Garmin's undocumented limits)
- **Docker profiles**: `garmin-cli` uses `profiles: ["cli"]` so it doesn't auto-start with `docker compose up`
- **Retries**: Tenacity with exponential backoff (5s initial, 120s max, 3 attempts) on API calls
- **MCP read-only**: `execute_sql` tool blocks INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE via regex; connections use `BEGIN READ ONLY`
- **Garmin date alignment**: Weeks are Monday–Sunday, periods exclude the current day. See `utils/date_ranges.py`.

## Testing

- **Async mode**: pytest-asyncio with `asyncio_mode = "auto"` (pyproject.toml)
- **Fixtures**: Sample Garmin JSON responses in `tests/fixtures/` (daily_summary.json, heart_rate.json, stress.json, sleep.json, activity_detail.json, activity_gps.json, endurance_score.json, hill_score.json, race_predictions.json, training_status.json, lactate_threshold.json, cycling_ftp.json, hydration_daily.json, gear.json, activity_laps.json, activity_weather.json)
- **Integration tests**: Use testcontainers to spin up real PostgreSQL + MongoDB — require Docker running
- **Code style**: ruff (line-length=100, target py312)

## Public Repository — Security

This repository is **public**. Always verify before committing or pushing:

- **No secrets**: Never commit `.env`, tokens, passwords, API keys, or credentials (real or generated). Use `.env.example` with placeholder values only.
- **No personal data**: No real email addresses, Garmin usernames, personal health data, IP addresses, or hostnames in code, comments, commit messages, or docs.
- **No sensitive paths**: Avoid hardcoding user home directories or local filesystem paths.
- **Commit messages**: Keep them descriptive but free of personal details.
- **Plan/spec files**: If they contain real credentials or personal info, add them to `.gitignore` — never commit them.
- **Review diffs**: Before every commit, review `git diff --staged` for accidental secret or PII exposure.
