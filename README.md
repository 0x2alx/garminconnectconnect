# garminconnectconnect

Self-hosted Garmin Connect data server. Polls your Garmin Connect account, stores health data in TimescaleDB (processed) and MongoDB (raw JSON), and exposes it via an MCP server for AI/LLM querying. Includes Grafana dashboards. Runs entirely in Docker.

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Garmin Connect  │────>│ garmin-server│────>│ TimescaleDB  │──> Grafana
│  (cloud API)     │     │ (polling     │     │ (processed   │    dashboards
└─────────────────┘     │  daemon)     │     │  health data)│
                        │              │────>│              │
                        │              │     └──────────────┘
                        │              │     ┌──────────────┐
                        │              │────>│   MongoDB     │
                        │              │     │ (raw JSON    │
                        └──────────────┘     │  archival)   │
                                             └──────────────┘
                        ┌──────────────┐
                        │  garmin-mcp  │──> Claude Code / AI tools
                        │ (MCP server) │    query your health data
                        └──────────────┘
```

**Data flow:** Garmin Connect API → garmin-server fetches every 10 min → raw JSON saved to MongoDB → processed metrics saved to TimescaleDB → Grafana visualizes, MCP server exposes to AI.

## Prerequisites

- Docker and Docker Compose (v2)
- A Garmin Connect account (the one linked to your Garmin watch/device)

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/0x2alx/garminconnectconnect.git
cd garminconnectconnect

# Recommended: generate random credentials for all services
./scripts/generate-secrets.sh
```

This creates a `.env` file with cryptographically random passwords for PostgreSQL, MongoDB, Grafana, and the MCP bearer token. If you prefer to set values manually, copy the example instead: `cp .env.example .env`.

Then edit `.env` with your Garmin credentials:

```env
GARMIN_EMAIL=your@email.com
GARMIN_PASSWORD=your_garmin_password
```

All other defaults work out of the box. See [Configuration](#configuration) for full options.

### 2. Build and start infrastructure

```bash
# Build the app image and start databases + Grafana
docker compose build
docker compose up -d timescaledb mongodb grafana
```

Wait a few seconds for the databases to initialize. You can check with:

```bash
docker compose ps
```

All services should show "healthy" or "running".

### 3. Login to Garmin Connect

```bash
docker compose run --rm garmin-cli login
```

This prompts for your email and password interactively. Tokens are saved to a Docker volume (`garmin_tokens`) and persist across container restarts. Tokens last ~1 year with auto-refresh.

If your account has MFA enabled, you'll be prompted for the code.

### 4. Backfill historical data

```bash
# Pull last 30 days of data (default)
docker compose run --rm garmin-cli backfill

# Pull last 90 days
docker compose run --rm garmin-cli backfill --days 90

# Force re-sync already synced dates
docker compose run --rm garmin-cli backfill --days 7 --force
```

This fetches data for each day across all metrics. Expect ~1-2 seconds per day due to Garmin API rate limits (1 request/second with 9 endpoints per day).

### 5. Start the polling daemon

```bash
docker compose up -d garmin-server
```

The daemon polls Garmin Connect every 10 minutes (configurable via `POLL_INTERVAL_MINUTES` in `.env`). It syncs:
- Today's data (force re-sync each cycle to get latest)
- Yesterday's data (catch any late-arriving data)
- Last 10 activities

The daemon auto-restarts on failure.

### 6. Set up TLS reverse proxy (optional but recommended)

First, edit `nginx/garmin-connect.conf` and replace `YOUR_HOST_IP` with your server's IP address. Then:

```bash
# Generate self-signed TLS certificates
sudo ./scripts/generate-certs.sh YOUR_HOST_IP

# Link nginx config and reload
sudo ln -sf $(pwd)/nginx/garmin-connect.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

This enables HTTPS access to Grafana (`https://YOUR_HOST_IP/grafana/`) and MCP (`https://YOUR_HOST_IP/mcp/sse`).

### 7. View your dashboards

Open [https://YOUR_HOST_IP/grafana/](https://YOUR_HOST_IP/grafana/) (or `http://localhost:3001` from the host) in your browser.

- **Username:** `admin`
- **Password:** whatever was set in `GRAFANA_PASSWORD` (use `scripts/generate-secrets.sh` to generate)

Navigate to **Dashboards > Garmin** to see the pre-built health dashboard.

## Stopping and Restarting

```bash
# Stop everything
docker compose down

# Stop everything and DELETE all data (databases, tokens, grafana)
docker compose down -v

# Stop only the daemon (keep databases running)
docker compose stop garmin-server

# Restart the daemon
docker compose restart garmin-server

# View logs
docker compose logs garmin-server
docker compose logs garmin-server -f    # follow/stream
docker compose logs garmin-server --tail 50  # last 50 lines

# Rebuild after code changes
docker compose build
docker compose up -d garmin-server
```

## CLI Reference

All CLI commands run via Docker:

```bash
docker compose run --rm garmin-cli <command> [options]
```

| Command | Description | Example |
|---------|-------------|---------|
| `login` | Authenticate with Garmin Connect | `docker compose run --rm garmin-cli login` |
| `backfill` | Pull historical data | `docker compose run --rm garmin-cli backfill --days 30` |
| `backfill --force` | Re-sync already completed dates | `docker compose run --rm garmin-cli backfill --days 7 --force` |
| `sync-one` | Sync a single endpoint for a single date | `docker compose run --rm garmin-cli sync-one --endpoint heart_rate --date 2025-01-15` |
| `daemon` | Start the polling daemon (foreground) | `docker compose run --rm garmin-cli daemon` |
| `mcp` | Start the MCP server | `docker compose run --rm garmin-cli mcp` |
| `status` | Show sync status per metric | `docker compose run --rm garmin-cli status` |
| `--help` | Show all commands | `docker compose run --rm garmin-cli --help` |

## MCP Server (AI/LLM Integration)

The MCP server lets AI tools like Claude Code query your health data directly. It requires bearer token authentication when `MCP_API_KEY` is set.

### Option A: stdio transport (local, recommended for Claude Code)

For local access, Claude Code connects via Docker stdio. No network exposure or bearer token needed:

```bash
claude mcp add garmin-health -s user -- \
  docker compose -f /path/to/garminconnectconnect/docker-compose.yml \
  run --rm --no-deps -T garmin-mcp
```

Replace `/path/to/garminconnectconnect` with the actual path to this repo on your machine.

### Option B: SSE transport (remote, via mcporter or direct)

For remote access, start the `garmin-mcp` Docker service:

```bash
docker compose up -d garmin-mcp
```

This starts the MCP server listening on `127.0.0.1:8080`. To expose it remotely, set up the [TLS reverse proxy](#6-set-up-tls-reverse-proxy-optional-but-recommended) and configure your MCP client (e.g., mcporter) with `~/.mcporter/mcporter.json`:

```json
{
  "mcpServers": {
    "garmin-health": {
      "baseUrl": "https://YOUR_HOST_IP/mcp/sse",
      "headers": {
        "Authorization": "Bearer <MCP_API_KEY>"
      }
    }
  }
}
```

Replace `<MCP_API_KEY>` with the value from your `.env` file.

### Available MCP Tools

Once connected, Claude can use these tools:

| Tool | Description |
|------|-------------|
| `list_tables` | List all health data tables with row counts |
| `get_table_schema` | Get column names and types for a table |
| `query_health_data` | Run pre-built queries (see below) |
| `execute_sql` | Run custom read-only SQL queries |
| `get_health_summary` | Get a comprehensive summary for a period (week, month, year, etc.) |
| `get_sync_status` | Check when each metric was last synced |

### Pre-built Queries

Use with `query_health_data(query_name, start_date, end_date)`. You can also pass a `period` parameter (e.g., `"week"`, `"4weeks"`, `"month"`, `"year"`) instead of explicit dates -- periods use Garmin's Monday-to-Sunday week convention.

| Query Name | What it returns |
|------------|----------------|
| `daily_overview` | Steps, calories, RHR, stress, body battery, SpO2 |
| `sleep_trend` | Hours slept (deep/light/REM), sleep score |
| `hr_intraday` | Per-minute heart rate readings |
| `stress_intraday` | Per-3-minute stress readings |
| `activity_list` | Recent activities with distance, duration, HR |
| `activity_detail` | Detailed activity data (HR, speed, cadence, training effect, VO2max) |
| `training_readiness_trend` | Readiness score breakdown |
| `hrv_trend` | HRV weekly average and last night |
| `body_composition_trend` | Weight and body fat percentage |
| `weekly_comparison` | This week vs last week averages |
| `personal_records` | Per-activity-type bests (longest, fastest, most elevation) |
| `recovery_analysis` | Combined RHR, stress, sleep, HRV, and readiness data |

### Example Claude Code Prompts

Once the MCP server is connected, you can ask Claude things like:

- "How did I sleep this week?"
- "Show me my heart rate trend for the last month"
- "What's my average daily step count vs my goal?"
- "Compare my HRV trend with my training readiness"
- "When was my last run and how did it go?"

## Configuration

All configuration is via environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GARMIN_EMAIL` | (required) | Your Garmin Connect email |
| `GARMIN_PASSWORD` | (required) | Your Garmin Connect password |
| `POSTGRES_HOST` | `timescaledb` | PostgreSQL host (container name in Docker) |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `garmin` | Database name |
| `POSTGRES_USER` | `garmin` | Database user |
| `POSTGRES_PASSWORD` | `garmin_secret` | Database password (**change this**) |
| `MONGO_HOST` | `mongodb` | MongoDB host (container name in Docker) |
| `MONGO_PORT` | `27017` | MongoDB port |
| `MONGO_DB` | `garmin_raw` | MongoDB database name |
| `MONGO_ROOT_USER` | `garmin` | MongoDB root username |
| `MONGO_ROOT_PASSWORD` | (required) | MongoDB root password |
| `POLL_INTERVAL_MINUTES` | `10` | How often the daemon polls Garmin (minutes) |
| `BACKFILL_DAYS` | `30` | Default days for backfill command |
| `GRAFANA_PASSWORD` | `admin` | Grafana admin password (**change this**) |
| `GRAFANA_PORT` | `3001` | Host port for Grafana (localhost-only) |
| `MCP_TRANSPORT` | `stdio` | MCP transport: `stdio`, `sse`, or `streamable-http` |
| `MCP_HOST` | `0.0.0.0` | MCP server bind address |
| `MCP_PORT` | `8080` | MCP server port (localhost-only when via Docker) |
| `MCP_API_KEY` | (empty) | Bearer token for MCP server auth (empty = auth disabled) |

### Changing the poll interval

Edit `.env`:

```env
POLL_INTERVAL_MINUTES=5
```

Then restart:

```bash
docker compose restart garmin-server
```

**Note on rate limits:** Garmin does not publish official rate limits. Community experience suggests ~50 requests per 10 minutes is safe. The default 10-minute interval with ~9 endpoints per cycle is well within limits. Polling more frequently than every 5 minutes is not recommended.

## Data Stored

### TimescaleDB (processed, queryable)

| Table | Granularity | Key Data |
|-------|-------------|----------|
| `daily_summary` | 1 per day | Steps, calories, distance, floors, HR, stress, body battery, SpO2, respiration, hydration |
| `body_composition` | Per weigh-in | Weight, BMI, body fat %, muscle mass, bone mass, body water % |
| `heart_rate` | ~1 per minute | Heart rate readings (hypertable) |
| `stress` | ~3 minutes | Stress level 1-100 (hypertable) |
| `body_battery` | ~3 minutes | Body battery 0-100 (hypertable) |
| `spo2` | Periodic | Blood oxygen saturation % (hypertable) |
| `respiration` | Periodic | Breaths per minute (hypertable) |
| `sleep_summary` | 1 per night | Sleep stages, duration, score, SpO2, respiration, HRV |
| `sleep_stages` | Per stage | Deep/light/REM/awake transitions (hypertable) |
| `activities` | Per activity | Type, distance, duration, HR, speed, cadence, training effect, VO2max |
| `activity_trackpoints` | Per second | GPS, HR, cadence, speed, power, altitude |
| `hrv` | 1 per day | Weekly avg, last night avg, baseline, status |
| `training_readiness` | 1 per day | Score, sleep/recovery/HRV components |
| `training_status` | 1 per day | Status, weekly load, VO2max, fitness age |
| `race_predictions` | 1 per day | 5K, 10K, half-marathon, marathon times |
| `sync_status` | Per metric per day | Tracking what has been synced |

Tables marked "hypertable" use TimescaleDB time-series partitioning for efficient queries on large datasets.

### MongoDB (raw JSON archival)

Every API response is stored as-is in MongoDB under collections named `raw_<endpoint>` (e.g., `raw_daily_summary`, `raw_heart_rate`). This is for:

- Future reprocessing if the data model changes
- Debugging API response formats
- Accessing fields not yet mapped to the processed schema

## Grafana Dashboard

The pre-built dashboard includes 15 panels:

| Panel | Type | Description |
|-------|------|-------------|
| Daily Steps | Bar chart | Color-coded: red (<5K), yellow (5-10K), green (>10K) |
| Daily Calories | Stacked bars | Active vs BMR calories |
| Resting Heart Rate | Line | RHR trend over time |
| Heart Rate (Intraday) | Line | Per-minute heart rate |
| Stress Level (Intraday) | Line | Continuous color scale (low=blue, high=red) |
| Body Battery | Area | 0-100% with green-to-red gradient |
| SpO2 | Scatter | Blood oxygen readings |
| Sleep Duration & Score | Stacked bars + line | Deep/light/REM hours with score overlay |
| HRV Trend | Dual line | Weekly average vs last night |
| Training Readiness | Bar | Score with color gradient |
| Average Stress | Bar | Daily average |
| Body Composition | Dual-axis line | Weight (left) + body fat % (right) |
| Recent Activities | Table | Last 50 activities with details |
| Respiration Rate | Line | Breaths per minute |
| Floors Climbed | Bar | Daily floor count |

The dashboard defaults to a 30-day view. Use Grafana's time picker to zoom in/out.

You can also create your own dashboards — the TimescaleDB datasource is pre-configured and all tables are available for querying.

## Docker Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `timescaledb` | `timescale/timescaledb:latest-pg16` | Internal only | Processed health data |
| `mongodb` | `mongo:7` | Internal only | Raw JSON archival |
| `grafana` | `grafana/grafana:latest` | 127.0.0.1:3001 | Dashboards (via nginx: `/grafana/`) |
| `garmin-server` | Built from Dockerfile | - | Polling daemon |
| `garmin-cli` | Built from Dockerfile | - | Interactive CLI (profiles: cli) |
| `garmin-mcp` | Built from Dockerfile | 127.0.0.1:8080 | MCP server (via nginx: `/mcp/`) |

### Docker Volumes

| Volume | Purpose | Warning |
|--------|---------|---------|
| `timescaledb_data` | All processed health data | `docker compose down -v` deletes this |
| `mongodb_data` | All raw JSON responses | `docker compose down -v` deletes this |
| `grafana_data` | Grafana settings and custom dashboards | `docker compose down -v` deletes this |
| `garmin_tokens` | Garmin OAuth tokens | `docker compose down -v` deletes this (re-login required) |

**Backup tip:** To back up your data, dump the TimescaleDB volume:

```bash
docker compose exec timescaledb pg_dump -U garmin garmin > backup.sql
```

To restore:

```bash
cat backup.sql | docker compose exec -T timescaledb psql -U garmin garmin
```

## Security

This project is designed to run on a private server (e.g., a home server or VPS). The default configuration follows a defense-in-depth approach:

**Network isolation:**
- Database ports (PostgreSQL, MongoDB) are **not exposed** to the host network at all -- they are only accessible within the Docker network.
- Grafana and MCP server bind to **127.0.0.1 only** -- they are not reachable from other machines without a reverse proxy.

**TLS termination:**
- The included nginx config (`nginx/garmin-connect.conf`) provides HTTPS with self-signed certificates.
- Run `scripts/generate-certs.sh` to generate a 10-year self-signed cert with your server's IP as the SAN.
- TLS 1.2+ only, with strong ciphers.

**Authentication:**
- **MCP server:** Bearer token authentication via `MCP_API_KEY`. When set, every HTTP request must include `Authorization: Bearer <key>`. When using stdio transport (local Claude Code), no token is needed.
- **Grafana:** Password-protected admin account. Use `scripts/generate-secrets.sh` to generate a strong random password.
- **Databases:** Password-protected with credentials generated by `scripts/generate-secrets.sh`.

**Credential management:**
- `scripts/generate-secrets.sh` generates cryptographically random passwords for all services.
- Garmin OAuth tokens are stored in a Docker volume (`garmin_tokens`) and auto-refresh for ~1 year.
- The `.env` file contains all secrets -- it is gitignored and should never be committed.

**Recommendations:**
- Always run `scripts/generate-secrets.sh` before first start -- do not use default passwords.
- If exposing to the internet, set up the TLS reverse proxy and ensure `MCP_API_KEY` is set.
- Consider firewall rules to restrict access to your server's IP.

## Garmin API Endpoints Polled

The server polls 30 Garmin Connect API endpoints across 7 categories:

**Daily Health:** daily summary, steps, stats, hydration

**Monitoring (intraday):** heart rate, stress, body battery, respiration, SpO2, steps intraday

**Sleep:** sleep data with stages, SpO2, respiration, HRV

**Activities:** activity list, details, splits, HR zones, weather, GPS trackpoints

**Training & Performance:** training readiness, training status, HRV, VO2max, fitness age, race predictions, endurance score, hill score, training load

**Body Composition:** weight, body fat, muscle mass, BMI

**Device:** connected devices, solar data

## Troubleshooting

### "No stored tokens and no credentials provided"

Run `docker compose run --rm garmin-cli login` first.

### Rate limit errors (HTTP 429)

Garmin has locked your account temporarily. Wait 1-2 hours and try again. Increase `POLL_INTERVAL_MINUTES` if this happens frequently (higher value = less frequent polling).

### Daemon keeps restarting

Check logs: `docker compose logs garmin-server --tail 100`

Common causes:
- Invalid credentials — run `login` again
- Database not ready — check `docker compose ps` for healthy status
- Rate limiting — increase `POLL_INTERVAL_MINUTES` to poll less frequently

### Grafana shows "No data"

1. Check that the daemon is running: `docker compose ps garmin-server`
2. Check sync status: `docker compose run --rm garmin-cli status`
3. Make sure you've run `backfill` at least once
4. Check the time range in Grafana (default is last 30 days)

### Rebuilding after code changes

```bash
docker compose build
docker compose up -d garmin-server
```

### Accessing the databases directly

Database ports are not exposed to the host network. Access them via Docker exec:

```bash
# PostgreSQL / TimescaleDB
docker compose exec timescaledb psql -U garmin garmin

# MongoDB (with authentication)
docker compose exec mongodb mongosh -u garmin -p "$MONGO_ROOT_PASSWORD" garmin_raw
```

**Note:** `psql -h localhost` and `mongosh --host localhost` will not work — database ports are only accessible within the Docker network.

## Development

### Running tests

```bash
# Unit tests (no Docker needed)
pip install -e ".[dev]"
pytest tests/ --ignore=tests/test_integration.py -v

# Integration tests (needs Docker)
pytest tests/test_integration.py -v
```

### Project structure

```
src/garminconnect/
  auth/client.py         # Garth-based Garmin authentication
  api/endpoints.py       # 30 API endpoint definitions
  api/client.py          # API client with rate limiting
  models/                # SQLAlchemy models (16 tables)
    daily.py             # DailySummary, BodyComposition
    monitoring.py        # HeartRate, Stress, BodyBattery, SpO2, Respiration
    sleep.py             # SleepSummary, SleepStages
    activities.py        # Activity, ActivityTrackpoint
    training.py          # HRV, TrainingReadiness, TrainingStatus, RacePrediction
    sync_status.py       # Sync tracking
  db/
    postgres.py          # TimescaleDB connection + hypertable setup
    mongo.py             # MongoDB connection
    repository.py        # Unified read/write abstraction
  sync/
    extractors.py        # Raw JSON -> SQLAlchemy model transforms
    pipeline.py          # Fetch -> store raw -> transform -> store processed
    scheduler.py         # APScheduler polling daemon
  mcp/
    server.py            # FastMCP server (6 tools) + bearer auth middleware
    tools.py             # SQL query templates (12 pre-built queries)
  cli/commands.py        # Click CLI (login, backfill, sync-one, daemon, mcp, status)
  config.py              # Pydantic settings (all env vars)
  utils/date_ranges.py   # Garmin-aligned date range helpers
```

## License

MIT
