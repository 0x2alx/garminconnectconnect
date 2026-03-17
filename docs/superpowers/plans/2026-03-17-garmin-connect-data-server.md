# Garmin Connect Data Server — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-hosted server that continuously polls Garmin Connect, stores raw responses in MongoDB and processed data in PostgreSQL/TimescaleDB, and exposes everything via an MCP server for AI/LLM querying.

**Architecture:** Fork garmy as the foundation. Replace SQLite with TimescaleDB (PostgreSQL) for processed health data. Add MongoDB for raw JSON archival. Add a daemon-mode polling scheduler. Expand from 11 to 25+ metrics using garmin-grafana's endpoint knowledge. Replace self-rolled auth with garth. Enhance the MCP server to query PostgreSQL instead of SQLite. Dockerize the full stack.

**Tech Stack:**
- Python 3.12+, FastMCP, SQLAlchemy 2.0, garth, PyMongo (sync MongoDB driver)
- PostgreSQL 16 + TimescaleDB extension
- MongoDB 7
- Docker Compose
- Optional: Grafana for visualization

---

## File Structure

```
garminconnectconnect/
├── docker-compose.yml                    # Full stack: app, timescaledb, mongodb, grafana
├── Dockerfile                            # Multi-stage Python build
├── pyproject.toml                        # Project config, deps, entry points
├── .env.example                          # Template for credentials/config
├── alembic.ini                           # DB migration config
├── alembic/
│   ├── env.py                            # Migration environment
│   └── versions/                         # Migration scripts
├── src/garminconnect/
│   ├── __init__.py
│   ├── __main__.py                       # CLI entry point
│   ├── config.py                         # App config (env vars, defaults)
│   ├── auth/
│   │   ├── __init__.py
│   │   └── client.py                     # garth-based auth wrapper
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py                     # Garmin Connect API client
│   │   └── endpoints.py                  # All endpoint definitions (25+)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                       # SQLAlchemy base, TimescaleDB hypertable setup
│   │   ├── daily.py                      # Daily summary, weight, body composition
│   │   ├── monitoring.py                 # HR, stress, body battery, SpO2, respiration (time-series)
│   │   ├── sleep.py                      # Sleep events and stages
│   │   ├── activities.py                 # Activities, laps, trackpoints
│   │   ├── training.py                   # HRV, VO2max, training readiness/status/load
│   │   └── sync_status.py               # Sync tracking per metric per date
│   ├── db/
│   │   ├── __init__.py
│   │   ├── postgres.py                   # TimescaleDB connection, session factory
│   │   ├── mongo.py                      # MongoDB connection, raw data storage
│   │   └── repository.py                 # Data access layer (read/write abstractions)
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── scheduler.py                  # Polling daemon (APScheduler)
│   │   ├── pipeline.py                   # Fetch -> store raw -> transform -> store processed
│   │   └── extractors.py                 # Raw JSON -> SQLAlchemy model transformers
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py                     # FastMCP server with 10+ tools
│   │   └── tools.py                      # Individual MCP tool definitions
│   └── cli/
│       ├── __init__.py
│       └── commands.py                   # CLI commands: sync, serve, backfill, status
└── tests/
    ├── conftest.py                       # Shared pytest fixtures
    ├── test_auth.py
    ├── test_api_client.py
    ├── test_models.py
    ├── test_extractors.py
    ├── test_sync_pipeline.py
    ├── test_scheduler.py
    ├── test_repository.py
    ├── test_mcp_server.py
    └── fixtures/                         # Sample Garmin API JSON responses
        ├── daily_summary.json
        ├── heart_rate.json
        ├── sleep.json
        ├── stress.json
        ├── activities.json
        └── ...
```

---

## Task 1: Project Scaffolding and Docker Stack

**Files:**
- Create: `pyproject.toml`
- Create: `docker-compose.yml`
- Create: `Dockerfile`
- Create: `.env.example`
- Create: `src/garminconnect/__init__.py`
- Create: `src/garminconnect/config.py`

- [ ] **Step 1: Create `pyproject.toml` with dependencies**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "garminconnectconnect"
version = "0.1.0"
description = "Self-hosted Garmin Connect data server with MCP integration"
requires-python = ">=3.12"
dependencies = [
    "garth>=0.6.0",
    "sqlalchemy>=2.0.0",
    "psycopg[binary]>=3.1.0",
    "pymongo>=4.6.0",
    "alembic>=1.13.0",
    "apscheduler>=3.10.0,<4.0.0",
    "fastmcp>=0.4.0",
    "click>=8.1.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
    "structlog>=24.1.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.3.0",
    "mypy>=1.8.0",
    "testcontainers[postgres,mongodb]>=4.0.0",
]
grafana = []

[project.scripts]
garmin-server = "garminconnect.cli.commands:cli"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create `.env.example`**

```env
# Garmin Connect Credentials
GARMIN_EMAIL=your@email.com
GARMIN_PASSWORD=your_password

# PostgreSQL / TimescaleDB
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=garmin
POSTGRES_USER=garmin
POSTGRES_PASSWORD=garmin_secret

# MongoDB
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=garmin_raw

# Polling
POLL_INTERVAL_MINUTES=10
BACKFILL_DAYS=30

# MCP
MCP_TRANSPORT=stdio
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: garmin
      POSTGRES_USER: garmin
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-garmin_secret}
    ports:
      - "5432:5432"
    volumes:
      - timescaledb_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U garmin"]
      interval: 5s
      timeout: 5s
      retries: 5

  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 5s
      timeout: 5s
      retries: 5

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      timescaledb:
        condition: service_healthy

  garmin-server:
    build: .
    env_file: .env
    depends_on:
      timescaledb:
        condition: service_healthy
      mongodb:
        condition: service_healthy
    volumes:
      - garmin_tokens:/app/tokens
    command: ["garmin-server", "daemon"]

volumes:
  timescaledb_data:
  mongodb_data:
  grafana_data:
  garmin_tokens:
```

- [ ] **Step 4: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir build && python -m build

FROM python:3.12-slim
WORKDIR /app
RUN useradd -m -u 1000 appuser
COPY --from=builder /app/dist/*.whl .
RUN pip install --no-cache-dir *.whl && rm *.whl
USER appuser
ENTRYPOINT ["garmin-server"]
```

- [ ] **Step 5: Create `src/garminconnect/__init__.py` and `config.py`**

`src/garminconnect/__init__.py`:
```python
"""Garmin Connect data server with MCP integration."""

__version__ = "0.1.0"
```

`src/garminconnect/config.py`:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "", "env_file": ".env"}

    garmin_email: str = ""
    garmin_password: str = ""
    garmin_token_dir: str = "~/.garminconnect"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "garmin"
    postgres_user: str = "garmin"
    postgres_password: str = "garmin_secret"

    mongo_host: str = "localhost"
    mongo_port: int = 27017
    mongo_db: str = "garmin_raw"

    poll_interval_minutes: int = 10
    backfill_days: int = 30

    mcp_transport: str = "stdio"

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def mongo_url(self) -> str:
        return f"mongodb://{self.mongo_host}:{self.mongo_port}"


settings = Settings()
```

- [ ] **Step 6: Verify project installs**

Run: `cd /home/alx/CODE/0x2alx_github/garminconnectconnect && pip install -e ".[dev]"`
Expected: Installs successfully with all dependencies

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml docker-compose.yml Dockerfile .env.example src/garminconnect/__init__.py src/garminconnect/config.py
git commit -m "feat: project scaffolding with Docker stack (TimescaleDB + MongoDB + Grafana)"
```

---

## Task 2: Auth Layer (garth-based)

**Files:**
- Create: `src/garminconnect/auth/__init__.py`
- Create: `src/garminconnect/auth/client.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write failing test for auth client**

```python
# tests/test_auth.py
from unittest.mock import patch, MagicMock
from garminconnect.auth.client import GarminAuth


def test_auth_login_stores_tokens(tmp_path):
    with patch("garminconnect.auth.client.garth") as mock_garth:
        auth = GarminAuth(token_dir=str(tmp_path))
        auth.login("test@email.com", "password123")
        mock_garth.login.assert_called_once_with("test@email.com", "password123")
        mock_garth.save.assert_called_once_with(str(tmp_path))


def test_auth_resume_from_tokens(tmp_path):
    with patch("garminconnect.auth.client.garth") as mock_garth:
        auth = GarminAuth(token_dir=str(tmp_path))
        auth.resume()
        mock_garth.resume.assert_called_once_with(str(tmp_path))


def test_auth_connectapi_delegates_to_garth():
    with patch("garminconnect.auth.client.garth") as mock_garth:
        mock_garth.connectapi.return_value = {"steps": 5000}
        auth = GarminAuth()
        result = auth.connectapi("/endpoint")
        mock_garth.connectapi.assert_called_once_with("/endpoint", params=None)
        assert result == {"steps": 5000}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement auth client**

```python
# src/garminconnect/auth/__init__.py
from garminconnect.auth.client import GarminAuth

__all__ = ["GarminAuth"]
```

```python
# src/garminconnect/auth/client.py
from __future__ import annotations

import os
from typing import Any

import garth
import structlog

logger = structlog.get_logger()


class GarminAuth:
    """Garth-based authentication for Garmin Connect."""

    def __init__(self, token_dir: str = "~/.garminconnect"):
        self.token_dir = os.path.expanduser(token_dir)

    def login(self, email: str, password: str) -> None:
        garth.login(email, password)
        garth.save(self.token_dir)
        logger.info("logged_in", email=email)

    def resume(self) -> None:
        garth.resume(self.token_dir)
        logger.info("resumed_session", token_dir=self.token_dir)

    def connectapi(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return garth.connectapi(endpoint, params=params)

    def ensure_authenticated(self, email: str = "", password: str = "") -> None:
        try:
            self.resume()
        except Exception:
            if not email or not password:
                raise ValueError("No stored tokens and no credentials provided")
            self.login(email, password)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/garminconnect/auth/ tests/test_auth.py
git commit -m "feat: garth-based auth client with token persistence"
```

---

## Task 3: API Client and Endpoint Registry

**Files:**
- Create: `src/garminconnect/api/__init__.py`
- Create: `src/garminconnect/api/endpoints.py`
- Create: `src/garminconnect/api/client.py`
- Create: `tests/test_api_client.py`
- Create: `tests/fixtures/` (sample JSON responses)

- [ ] **Step 1: Define all endpoints**

```python
# src/garminconnect/api/endpoints.py
"""All Garmin Connect API endpoint definitions.

Endpoint URLs sourced from python-garminconnect (127+ methods) and
garmin-grafana (20+ measurement types). Each endpoint defines:
- name: unique identifier
- url_template: with {date}, {user_id}, {start}, {end} placeholders
- category: for grouping (daily, monitoring, sleep, activity, training, body)
- requires_user_id: whether the endpoint needs the display name / user ID
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EndpointCategory(Enum):
    DAILY = "daily"
    MONITORING = "monitoring"
    SLEEP = "sleep"
    ACTIVITY = "activity"
    TRAINING = "training"
    BODY = "body"
    DEVICE = "device"


@dataclass(frozen=True)
class Endpoint:
    name: str
    url_template: str
    category: EndpointCategory
    requires_user_id: bool = False
    params: dict[str, str] | None = None


# fmt: off
ENDPOINTS: list[Endpoint] = [
    # === DAILY HEALTH ===
    Endpoint("daily_summary",       "/usersummary-service/usersummary/daily/{user_id}?calendarDate={date}",     EndpointCategory.DAILY, requires_user_id=True),
    Endpoint("daily_steps",         "/usersummary-service/stats/steps/daily/{start}/{end}",                     EndpointCategory.DAILY),
    Endpoint("daily_stats",         "/userstats-service/wellness/daily/{user_id}?fromDate={start}&untilDate={end}", EndpointCategory.DAILY, requires_user_id=True),
    Endpoint("hydration",           "/usersummary-service/usersummary/hydration/allData/{date}",                EndpointCategory.DAILY),

    # === MONITORING (INTRADAY TIME-SERIES) ===
    Endpoint("heart_rate",          "/wellness-service/wellness/dailyHeartRate/{user_id}?date={date}",           EndpointCategory.MONITORING, requires_user_id=True),
    Endpoint("stress",              "/wellness-service/wellness/dailyStress/{date}",                            EndpointCategory.MONITORING),
    Endpoint("body_battery",        "/wellness-service/wellness/bodyBattery/date/{date}",                       EndpointCategory.MONITORING),
    Endpoint("respiration",         "/wellness-service/wellness/daily/respiration/{date}",                      EndpointCategory.MONITORING),
    Endpoint("spo2",                "/wellness-service/wellness/daily/spo2/{date}",                             EndpointCategory.MONITORING),
    Endpoint("steps_intraday",      "/wellness-service/wellness/dailySummaryChart/{user_id}?date={date}",       EndpointCategory.MONITORING, requires_user_id=True),

    # === SLEEP ===
    Endpoint("sleep",               "/wellness-service/wellness/dailySleepData/{user_id}?date={date}&nonSleepBufferMinutes=60", EndpointCategory.SLEEP, requires_user_id=True),

    # === ACTIVITIES ===
    Endpoint("activity_list",       "/activitylist-service/activities/search/activities",                       EndpointCategory.ACTIVITY),
    Endpoint("activity_detail",     "/activity-service/activity/{activity_id}",                                 EndpointCategory.ACTIVITY),
    Endpoint("activity_splits",     "/activity-service/activity/{activity_id}/splits",                          EndpointCategory.ACTIVITY),
    Endpoint("activity_hr_zones",   "/activity-service/activity/{activity_id}/hrTimeInZones",                   EndpointCategory.ACTIVITY),
    Endpoint("activity_weather",    "/activity-service/activity/{activity_id}/weather",                         EndpointCategory.ACTIVITY),
    Endpoint("activity_gps",        "/activity-service/activity/{activity_id}/details",                         EndpointCategory.ACTIVITY),

    # === TRAINING & PERFORMANCE ===
    Endpoint("training_readiness",  "/metrics-service/metrics/trainingreadiness/{date}",                        EndpointCategory.TRAINING),
    Endpoint("training_status",     "/metrics-service/metrics/trainingstatus/aggregated/{date}",                EndpointCategory.TRAINING),
    Endpoint("hrv",                 "/hrv-service/hrv/{date}",                                                  EndpointCategory.TRAINING),
    Endpoint("vo2max",              "/metrics-service/metrics/maxmet/daily/{start}/{end}",                      EndpointCategory.TRAINING),
    Endpoint("fitness_age",         "/fitnessage-service/fitnessage",                                           EndpointCategory.TRAINING),
    Endpoint("race_predictions",    "/metrics-service/metrics/racepredictions",                                  EndpointCategory.TRAINING),
    Endpoint("endurance_score",     "/metrics-service/metrics/endurancescore",                                   EndpointCategory.TRAINING),
    Endpoint("hill_score",          "/metrics-service/metrics/hillscore",                                        EndpointCategory.TRAINING),
    Endpoint("training_load",       "/metrics-service/metrics/trainingload/weekly",                              EndpointCategory.TRAINING),

    # === BODY COMPOSITION ===
    Endpoint("weight",              "/weight-service/weight/dateRange?startDate={start}&endDate={end}",          EndpointCategory.BODY),
    Endpoint("body_composition",    "/weight-service/weight/daterangesnapshot?startDate={start}&endDate={end}",  EndpointCategory.BODY),

    # === DEVICE ===
    Endpoint("devices",             "/device-service/deviceregistration/devices",                                EndpointCategory.DEVICE),
    Endpoint("device_solar",        "/web-gateway/solar/{date}/{device_id}",                                    EndpointCategory.DEVICE),
]
# fmt: on

ENDPOINTS_BY_NAME: dict[str, Endpoint] = {ep.name: ep for ep in ENDPOINTS}
```

- [ ] **Step 2: Write failing test for API client**

```python
# tests/test_api_client.py
from unittest.mock import MagicMock
from datetime import date
from garminconnect.api.client import GarminAPIClient
from garminconnect.api.endpoints import ENDPOINTS_BY_NAME


def test_fetch_daily_summary():
    mock_auth = MagicMock()
    mock_auth.connectapi.return_value = {"totalSteps": 8000, "totalCalories": 2100}
    client = GarminAPIClient(auth=mock_auth, user_id="test_user")
    result = client.fetch("daily_summary", date=date(2026, 3, 17))
    assert result["totalSteps"] == 8000
    mock_auth.connectapi.assert_called_once()


def test_fetch_stress_no_user_id_needed():
    mock_auth = MagicMock()
    mock_auth.connectapi.return_value = {"stressData": []}
    client = GarminAPIClient(auth=mock_auth, user_id="test_user")
    result = client.fetch("stress", date=date(2026, 3, 17))
    call_url = mock_auth.connectapi.call_args[0][0]
    assert "test_user" not in call_url


def test_fetch_unknown_endpoint_raises():
    mock_auth = MagicMock()
    client = GarminAPIClient(auth=mock_auth, user_id="test_user")
    try:
        client.fetch("nonexistent_endpoint", date=date(2026, 3, 17))
        assert False, "Should have raised"
    except KeyError:
        pass


def test_all_endpoints_have_unique_names():
    names = [ep.name for ep in ENDPOINTS_BY_NAME.values()]
    assert len(names) == len(set(names))
```

- [ ] **Step 3: Implement API client**

```python
# src/garminconnect/api/__init__.py
from garminconnect.api.client import GarminAPIClient

__all__ = ["GarminAPIClient"]
```

```python
# src/garminconnect/api/client.py
from __future__ import annotations

import time
from datetime import date
from typing import Any

import structlog

from garminconnect.api.endpoints import ENDPOINTS_BY_NAME, Endpoint
from garminconnect.auth.client import GarminAuth

logger = structlog.get_logger()

# Garmin rate limit safety: minimum seconds between API calls
MIN_REQUEST_INTERVAL = 1.0


class GarminAPIClient:
    """Fetches data from Garmin Connect API endpoints."""

    def __init__(self, auth: GarminAuth, user_id: str = ""):
        self.auth = auth
        self.user_id = user_id
        self._last_request_time: float = 0

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()

    def _build_url(
        self,
        endpoint: Endpoint,
        date: date | None = None,
        start: date | None = None,
        end: date | None = None,
        activity_id: str | None = None,
        device_id: str | None = None,
    ) -> str:
        url = endpoint.url_template
        replacements: dict[str, str] = {}
        if date:
            replacements["{date}"] = date.isoformat()
        if start:
            replacements["{start}"] = start.isoformat()
        if end:
            replacements["{end}"] = end.isoformat()
        if endpoint.requires_user_id:
            replacements["{user_id}"] = self.user_id
        if activity_id:
            replacements["{activity_id}"] = activity_id
        if device_id:
            replacements["{device_id}"] = device_id
        for placeholder, value in replacements.items():
            url = url.replace(placeholder, value)
        return url

    def fetch(self, endpoint_name: str, params: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        endpoint = ENDPOINTS_BY_NAME[endpoint_name]
        url = self._build_url(endpoint, **kwargs)
        self._rate_limit()
        logger.debug("fetching", endpoint=endpoint_name, url=url)
        return self.auth.connectapi(url, params=params)

    def fetch_all_daily(self, target_date: date) -> dict[str, Any]:
        results: dict[str, Any] = {}
        daily_endpoints = [
            ep for ep in ENDPOINTS_BY_NAME.values()
            if ep.category.value in ("daily", "monitoring", "sleep", "training")
            and "{activity_id}" not in ep.url_template
            and "{device_id}" not in ep.url_template
            and "{start}" not in ep.url_template
        ]
        for ep in daily_endpoints:
            try:
                results[ep.name] = self.fetch(ep.name, date=target_date)
            except Exception as e:
                logger.warning("fetch_failed", endpoint=ep.name, error=str(e))
                results[ep.name] = None
        return results
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_api_client.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/garminconnect/api/ tests/test_api_client.py
git commit -m "feat: API client with 30 endpoint definitions and rate limiting"
```

---

## Task 4: PostgreSQL/TimescaleDB Models

**Files:**
- Create: `src/garminconnect/models/__init__.py`
- Create: `src/garminconnect/models/base.py`
- Create: `src/garminconnect/models/daily.py`
- Create: `src/garminconnect/models/monitoring.py`
- Create: `src/garminconnect/models/sleep.py`
- Create: `src/garminconnect/models/activities.py`
- Create: `src/garminconnect/models/training.py`
- Create: `src/garminconnect/models/sync_status.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing test for models**

```python
# tests/test_models.py
from datetime import date, datetime, timezone
from garminconnect.models.daily import DailySummary
from garminconnect.models.monitoring import HeartRateReading, StressReading
from garminconnect.models.sleep import SleepSummary
from garminconnect.models.activities import Activity
from garminconnect.models.training import HRVSummary
from garminconnect.models.sync_status import SyncStatus


def test_daily_summary_creation():
    s = DailySummary(
        date=date(2026, 3, 17),
        total_steps=8000,
        total_calories=2100,
        total_distance_meters=6400.0,
        resting_heart_rate=58,
    )
    assert s.total_steps == 8000
    assert s.date == date(2026, 3, 17)


def test_heart_rate_reading():
    hr = HeartRateReading(
        timestamp=datetime(2026, 3, 17, 10, 30, tzinfo=timezone.utc),
        heart_rate=72,
    )
    assert hr.heart_rate == 72


def test_stress_reading():
    s = StressReading(
        timestamp=datetime(2026, 3, 17, 10, 30, tzinfo=timezone.utc),
        stress_level=45,
    )
    assert s.stress_level == 45


def test_sleep_summary():
    s = SleepSummary(
        date=date(2026, 3, 17),
        total_sleep_seconds=28800,
        deep_sleep_seconds=7200,
        light_sleep_seconds=14400,
        rem_sleep_seconds=5400,
        awake_seconds=1800,
        sleep_score=82,
    )
    assert s.sleep_score == 82


def test_activity_creation():
    a = Activity(
        activity_id="12345",
        activity_type="running",
        start_time=datetime(2026, 3, 17, 7, 0, tzinfo=timezone.utc),
        duration_seconds=3600,
        distance_meters=10000.0,
    )
    assert a.activity_type == "running"


def test_hrv_summary():
    h = HRVSummary(
        date=date(2026, 3, 17),
        weekly_avg=42.5,
        last_night_avg=38.0,
        status="BALANCED",
    )
    assert h.status == "BALANCED"


def test_sync_status():
    ss = SyncStatus(
        metric_name="daily_summary",
        date=date(2026, 3, 17),
        status="completed",
    )
    assert ss.status == "completed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — modules not found

- [ ] **Step 3: Implement base model**

```python
# src/garminconnect/models/__init__.py
"""SQLAlchemy models for Garmin health data in TimescaleDB."""

# src/garminconnect/models/base.py
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase, MappedAsDataclass):
    """Base class for all models. Uses mapped_as_dataclass for clean init."""
    pass
```

- [ ] **Step 4: Implement all model files**

```python
# src/garminconnect/models/daily.py
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class DailySummary(Base):
    __tablename__ = "daily_summary"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    total_steps: Mapped[int | None] = mapped_column(Integer, default=None)
    step_goal: Mapped[int | None] = mapped_column(Integer, default=None)
    total_calories: Mapped[int | None] = mapped_column(Integer, default=None)
    active_calories: Mapped[int | None] = mapped_column(Integer, default=None)
    bmr_calories: Mapped[int | None] = mapped_column(Integer, default=None)
    total_distance_meters: Mapped[float | None] = mapped_column(Float, default=None)
    floors_climbed: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    floors_goal: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    intensity_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    moderate_intensity_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    vigorous_intensity_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    resting_heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    min_heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    max_heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    avg_stress: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    max_stress: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    body_battery_high: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    body_battery_low: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    avg_spo2: Mapped[float | None] = mapped_column(Float, default=None)
    lowest_spo2: Mapped[float | None] = mapped_column(Float, default=None)
    avg_respiration: Mapped[float | None] = mapped_column(Float, default=None)
    hydration_ml: Mapped[int | None] = mapped_column(Integer, default=None)
    sweat_loss_ml: Mapped[int | None] = mapped_column(Integer, default=None)


class BodyComposition(Base):
    __tablename__ = "body_composition"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, default=None)
    bmi: Mapped[float | None] = mapped_column(Float, default=None)
    body_fat_pct: Mapped[float | None] = mapped_column(Float, default=None)
    muscle_mass_kg: Mapped[float | None] = mapped_column(Float, default=None)
    bone_mass_kg: Mapped[float | None] = mapped_column(Float, default=None)
    body_water_pct: Mapped[float | None] = mapped_column(Float, default=None)
```

```python
# src/garminconnect/models/monitoring.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class HeartRateReading(Base):
    __tablename__ = "heart_rate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    heart_rate: Mapped[int] = mapped_column(SmallInteger)


class StressReading(Base):
    __tablename__ = "stress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    stress_level: Mapped[int] = mapped_column(SmallInteger)


class BodyBatteryReading(Base):
    __tablename__ = "body_battery"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    level: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str | None] = mapped_column(default=None)


class SpO2Reading(Base):
    __tablename__ = "spo2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    spo2: Mapped[float] = mapped_column(Float)


class RespirationReading(Base):
    __tablename__ = "respiration"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    respiration_rate: Mapped[float] = mapped_column(Float)
```

```python
# src/garminconnect/models/sleep.py
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class SleepSummary(Base):
    __tablename__ = "sleep_summary"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    total_sleep_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    deep_sleep_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    light_sleep_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    rem_sleep_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    awake_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    sleep_score: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    sleep_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    sleep_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    avg_spo2: Mapped[float | None] = mapped_column(Float, default=None)
    avg_respiration: Mapped[float | None] = mapped_column(Float, default=None)
    avg_stress: Mapped[float | None] = mapped_column(Float, default=None)
    avg_hrv: Mapped[float | None] = mapped_column(Float, default=None)
    body_battery_change: Mapped[int | None] = mapped_column(SmallInteger, default=None)


class SleepStage(Base):
    __tablename__ = "sleep_stages"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    stage: Mapped[str] = mapped_column(String(20))  # deep, light, rem, awake
    duration_seconds: Mapped[int] = mapped_column(Integer)
```

```python
# src/garminconnect/models/activities.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class Activity(Base):
    __tablename__ = "activities"

    activity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    activity_type: Mapped[str | None] = mapped_column(String(50), default=None)
    sport: Mapped[str | None] = mapped_column(String(50), default=None)
    name: Mapped[str | None] = mapped_column(String(200), default=None)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    elapsed_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    distance_meters: Mapped[float | None] = mapped_column(Float, default=None)
    calories: Mapped[int | None] = mapped_column(Integer, default=None)
    avg_heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    max_heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    avg_speed: Mapped[float | None] = mapped_column(Float, default=None)
    max_speed: Mapped[float | None] = mapped_column(Float, default=None)
    elevation_gain: Mapped[float | None] = mapped_column(Float, default=None)
    elevation_loss: Mapped[float | None] = mapped_column(Float, default=None)
    avg_cadence: Mapped[float | None] = mapped_column(Float, default=None)
    avg_power: Mapped[float | None] = mapped_column(Float, default=None)
    training_effect_aerobic: Mapped[float | None] = mapped_column(Float, default=None)
    training_effect_anaerobic: Mapped[float | None] = mapped_column(Float, default=None)
    vo2max: Mapped[float | None] = mapped_column(Float, default=None)


class ActivityTrackpoint(Base):
    __tablename__ = "activity_trackpoints"

    activity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)
    altitude: Mapped[float | None] = mapped_column(Float, default=None)
    heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    cadence: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    speed: Mapped[float | None] = mapped_column(Float, default=None)
    power: Mapped[float | None] = mapped_column(Float, default=None)
```

```python
# src/garminconnect/models/training.py
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class HRVSummary(Base):
    __tablename__ = "hrv"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    weekly_avg: Mapped[float | None] = mapped_column(Float, default=None)
    last_night_avg: Mapped[float | None] = mapped_column(Float, default=None)
    last_night_5min_high: Mapped[float | None] = mapped_column(Float, default=None)
    baseline_low: Mapped[float | None] = mapped_column(Float, default=None)
    baseline_high: Mapped[float | None] = mapped_column(Float, default=None)
    status: Mapped[str | None] = mapped_column(String(30), default=None)


class TrainingReadiness(Base):
    __tablename__ = "training_readiness"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    score: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    level: Mapped[str | None] = mapped_column(String(30), default=None)
    sleep_score: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    recovery_score: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    hrv_score: Mapped[int | None] = mapped_column(SmallInteger, default=None)


class TrainingStatus(Base):
    __tablename__ = "training_status"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    training_status: Mapped[str | None] = mapped_column(String(50), default=None)
    weekly_load: Mapped[float | None] = mapped_column(Float, default=None)
    load_focus: Mapped[str | None] = mapped_column(String(50), default=None)
    vo2max_running: Mapped[float | None] = mapped_column(Float, default=None)
    vo2max_cycling: Mapped[float | None] = mapped_column(Float, default=None)
    fitness_age: Mapped[int | None] = mapped_column(SmallInteger, default=None)


class RacePrediction(Base):
    __tablename__ = "race_predictions"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    time_5k_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    time_10k_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    time_half_marathon_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    time_marathon_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
```

```python
# src/garminconnect/models/sync_status.py
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class SyncStatus(Base):
    __tablename__ = "sync_status"

    metric_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, completed, failed
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    error: Mapped[str | None] = mapped_column(String(500), default=None)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_models.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add src/garminconnect/models/ tests/test_models.py
git commit -m "feat: SQLAlchemy models for daily, monitoring, sleep, activities, training data"
```

---

## Task 5: Database Layer (TimescaleDB + MongoDB)

**Files:**
- Create: `src/garminconnect/db/__init__.py`
- Create: `src/garminconnect/db/postgres.py`
- Create: `src/garminconnect/db/mongo.py`
- Create: `src/garminconnect/db/repository.py`
- Create: `tests/test_repository.py`

- [ ] **Step 1: Write failing test for repository**

```python
# tests/test_repository.py
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from garminconnect.db.repository import HealthRepository
from garminconnect.models.daily import DailySummary


def test_upsert_daily_summary():
    mock_session = MagicMock()
    repo = HealthRepository(session_factory=lambda: mock_session)
    summary = DailySummary(
        date=date(2026, 3, 17),
        total_steps=8000,
        total_calories=2100,
    )
    repo.upsert(summary)
    mock_session.merge.assert_called_once()
    mock_session.commit.assert_called_once()


def test_store_raw_response():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)
    repo = HealthRepository(session_factory=MagicMock(), mongo_db=mock_db)
    repo.store_raw(
        endpoint="daily_summary",
        date=date(2026, 3, 17),
        data={"totalSteps": 8000},
    )
    mock_collection.replace_one.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_repository.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement database layer**

```python
# src/garminconnect/db/__init__.py
from garminconnect.db.postgres import create_engine_and_tables
from garminconnect.db.mongo import get_mongo_db
from garminconnect.db.repository import HealthRepository

__all__ = ["create_engine_and_tables", "get_mongo_db", "HealthRepository"]
```

```python
# src/garminconnect/db/postgres.py
from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from garminconnect.config import settings
from garminconnect.models.base import Base

# Import all models so they register with Base.metadata
import garminconnect.models.daily  # noqa: F401
import garminconnect.models.monitoring  # noqa: F401
import garminconnect.models.sleep  # noqa: F401
import garminconnect.models.activities  # noqa: F401
import garminconnect.models.training  # noqa: F401
import garminconnect.models.sync_status  # noqa: F401

# Tables to convert to TimescaleDB hypertables (high-frequency time-series)
HYPERTABLES = [
    ("heart_rate", "timestamp"),
    ("stress", "timestamp"),
    ("body_battery", "timestamp"),
    ("spo2", "timestamp"),
    ("respiration", "timestamp"),
    ("sleep_stages", "timestamp"),
]


def create_engine_and_tables(url: str | None = None) -> tuple[Engine, sessionmaker[Session]]:
    engine = create_engine(url or settings.postgres_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)

    # Create TimescaleDB hypertables for time-series tables
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        conn.commit()
        for table_name, time_col in HYPERTABLES:
            try:
                conn.execute(
                    text(
                        f"SELECT create_hypertable('{table_name}', '{time_col}', "
                        f"if_not_exists => TRUE, migrate_data => TRUE)"
                    )
                )
                conn.commit()
            except Exception:
                conn.rollback()

    factory = sessionmaker(engine)
    return engine, factory
```

```python
# src/garminconnect/db/mongo.py
from __future__ import annotations

from pymongo import MongoClient
from pymongo.database import Database

from garminconnect.config import settings


def get_mongo_client(url: str | None = None) -> MongoClient:
    return MongoClient(url or settings.mongo_url)


def get_mongo_db(url: str | None = None, db_name: str | None = None) -> Database:
    client = get_mongo_client(url)
    return client[db_name or settings.mongo_db]
```

```python
# src/garminconnect/db/repository.py
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session
from pymongo.database import Database

import structlog

from garminconnect.models.base import Base

logger = structlog.get_logger()


class HealthRepository:
    """Unified data access for PostgreSQL (processed) and MongoDB (raw)."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        mongo_db: Database | None = None,
    ):
        self._session_factory = session_factory
        self._mongo_db = mongo_db

    def upsert(self, model: Base) -> None:
        session = self._session_factory()
        try:
            session.merge(model)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def upsert_many(self, models: list[Base]) -> None:
        session = self._session_factory()
        try:
            for model in models:
                session.merge(model)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def store_raw(self, endpoint: str, date: date, data: Any) -> None:
        if self._mongo_db is None:
            return
        collection = self._mongo_db[f"raw_{endpoint}"]
        doc = {
            "endpoint": endpoint,
            "date": date.isoformat(),
            "fetched_at": datetime.now(timezone.utc),
            "data": data,
        }
        collection.replace_one(
            {"endpoint": endpoint, "date": date.isoformat()},
            doc,
            upsert=True,
        )
        logger.debug("stored_raw", endpoint=endpoint, date=date.isoformat())

    def get_sync_status(self, metric: str, target_date: date) -> str | None:
        from garminconnect.models.sync_status import SyncStatus

        session = self._session_factory()
        try:
            result = session.get(SyncStatus, (metric, target_date))
            return result.status if result else None
        finally:
            session.close()

    def mark_synced(self, metric: str, target_date: date, error: str | None = None) -> None:
        from garminconnect.models.sync_status import SyncStatus

        status = SyncStatus(
            metric_name=metric,
            date=target_date,
            status="failed" if error else "completed",
            synced_at=datetime.now(timezone.utc),
            error=error,
        )
        self.upsert(status)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_repository.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/garminconnect/db/ tests/test_repository.py
git commit -m "feat: database layer with TimescaleDB hypertables and MongoDB raw storage"
```

---

## Task 6: Data Extractors (Raw JSON -> Models)

**Files:**
- Create: `src/garminconnect/sync/__init__.py`
- Create: `src/garminconnect/sync/extractors.py`
- Create: `tests/test_extractors.py`
- Create: `tests/fixtures/daily_summary.json`
- Create: `tests/fixtures/heart_rate.json`
- Create: `tests/fixtures/sleep.json`
- Create: `tests/fixtures/stress.json`

- [ ] **Step 1: Create test fixtures from real Garmin API response shapes**

File: `tests/fixtures/daily_summary.json`
```json
{
  "totalSteps": 8432,
  "totalStepGoal": 10000,
  "totalKilocalories": 2156,
  "activeKilocalories": 876,
  "bmrKilocalories": 1280,
  "totalDistanceMeters": 6543.2,
  "floorsAscended": 8,
  "floorsAscendedGoal": 10,
  "intensityMinutesGoal": 150,
  "moderateIntensityMinutes": 45,
  "vigorousIntensityMinutes": 20,
  "restingHeartRate": 58,
  "minHeartRate": 48,
  "maxHeartRate": 142,
  "averageStressLevel": 35,
  "maxStressLevel": 78,
  "bodyBatteryHighestValue": 95,
  "bodyBatteryLowestValue": 22,
  "averageSpo2": 96.5,
  "lowestSpo2": 92.0,
  "averageRespirationValue": 16.2,
  "lastSevenDaysAvgRestingHeartRate": 57
}
```

File: `tests/fixtures/heart_rate.json`
```json
{
  "heartRateValues": [
    [1710662400000, 62],
    [1710662460000, 65],
    [1710662520000, 68],
    [1710662580000, null],
    [1710662640000, 70]
  ]
}
```

File: `tests/fixtures/stress.json`
```json
{
  "stressValuesArray": [
    [1710662400000, 25],
    [1710662580000, 32],
    [1710662760000, -1],
    [1710662940000, 45]
  ]
}
```

File: `tests/fixtures/sleep.json`
```json
{
  "dailySleepDTO": {
    "sleepTimeSeconds": 28800,
    "deepSleepSeconds": 7200,
    "lightSleepSeconds": 14400,
    "remSleepSeconds": 5400,
    "awakeSleepSeconds": 1800,
    "sleepStartTimestampGMT": 1710626400000,
    "sleepEndTimestampGMT": 1710655200000,
    "averageSpO2Value": 95.5,
    "averageRespirationValue": 15.8,
    "averageStress": 18.0,
    "bodyBatteryChange": 65,
    "overallSleepScore": { "value": 82 }
  }
}
```

- [ ] **Step 2: Write failing test for extractors**

```python
# tests/test_extractors.py
import json
from datetime import date
from pathlib import Path

from garminconnect.sync.extractors import (
    extract_daily_summary,
    extract_heart_rate_readings,
    extract_stress_readings,
    extract_sleep_summary,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_daily_summary():
    data = json.loads((FIXTURES / "daily_summary.json").read_text())
    result = extract_daily_summary(date(2026, 3, 17), data)
    assert result.total_steps == 8432
    assert result.resting_heart_rate == 58
    assert result.avg_spo2 == 96.5
    assert result.body_battery_high == 95


def test_extract_heart_rate_readings():
    data = json.loads((FIXTURES / "heart_rate.json").read_text())
    readings = extract_heart_rate_readings(data)
    assert len(readings) == 4  # null values skipped
    assert readings[0].heart_rate == 62


def test_extract_stress_readings():
    data = json.loads((FIXTURES / "stress.json").read_text())
    readings = extract_stress_readings(data)
    assert len(readings) == 3  # -1 values (rest/unmeasured) skipped
    assert readings[0].stress_level == 25


def test_extract_sleep_summary():
    data = json.loads((FIXTURES / "sleep.json").read_text())
    result = extract_sleep_summary(date(2026, 3, 17), data)
    assert result.total_sleep_seconds == 28800
    assert result.sleep_score == 82
    assert result.avg_spo2 == 95.5
    assert result.body_battery_change == 65
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_extractors.py -v`
Expected: FAIL — module not found

- [ ] **Step 4: Implement extractors**

```python
# src/garminconnect/sync/__init__.py
"""Sync pipeline: fetch, store raw, transform, store processed."""

# src/garminconnect/sync/extractors.py
"""Transform raw Garmin API JSON responses into SQLAlchemy model instances."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from garminconnect.models.daily import DailySummary, BodyComposition
from garminconnect.models.monitoring import (
    BodyBatteryReading,
    HeartRateReading,
    RespirationReading,
    SpO2Reading,
    StressReading,
)
from garminconnect.models.sleep import SleepSummary
from garminconnect.models.activities import Activity
from garminconnect.models.training import HRVSummary, TrainingReadiness


def _ts_to_dt(epoch_ms: int) -> datetime:
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)


def extract_daily_summary(target_date: date, data: dict[str, Any]) -> DailySummary:
    return DailySummary(
        date=target_date,
        total_steps=data.get("totalSteps"),
        step_goal=data.get("totalStepGoal"),
        total_calories=data.get("totalKilocalories"),
        active_calories=data.get("activeKilocalories"),
        bmr_calories=data.get("bmrKilocalories"),
        total_distance_meters=data.get("totalDistanceMeters"),
        floors_climbed=data.get("floorsAscended"),
        floors_goal=data.get("floorsAscendedGoal"),
        moderate_intensity_minutes=data.get("moderateIntensityMinutes"),
        vigorous_intensity_minutes=data.get("vigorousIntensityMinutes"),
        intensity_minutes=(data.get("moderateIntensityMinutes") or 0) + (data.get("vigorousIntensityMinutes") or 0) or None,
        resting_heart_rate=data.get("restingHeartRate"),
        min_heart_rate=data.get("minHeartRate"),
        max_heart_rate=data.get("maxHeartRate"),
        avg_stress=data.get("averageStressLevel"),
        max_stress=data.get("maxStressLevel"),
        body_battery_high=data.get("bodyBatteryHighestValue"),
        body_battery_low=data.get("bodyBatteryLowestValue"),
        avg_spo2=data.get("averageSpo2"),
        lowest_spo2=data.get("lowestSpo2"),
        avg_respiration=data.get("averageRespirationValue"),
        hydration_ml=data.get("hydrationIntakeMl"),
        sweat_loss_ml=data.get("sweatLossMl"),
    )


def extract_heart_rate_readings(data: dict[str, Any]) -> list[HeartRateReading]:
    readings = []
    for ts_ms, hr in data.get("heartRateValues", []):
        if hr is not None and ts_ms is not None:
            readings.append(HeartRateReading(timestamp=_ts_to_dt(ts_ms), heart_rate=hr))
    return readings


def extract_stress_readings(data: dict[str, Any]) -> list[StressReading]:
    readings = []
    for ts_ms, level in data.get("stressValuesArray", []):
        if level is not None and level >= 0 and ts_ms is not None:
            readings.append(StressReading(timestamp=_ts_to_dt(ts_ms), stress_level=level))
    return readings


def extract_body_battery_readings(data: dict[str, Any]) -> list[BodyBatteryReading]:
    readings = []
    for item in data if isinstance(data, list) else data.get("bodyBatteryValuesArray", []):
        ts_ms = item.get("startTimestampGMT") or item.get("timestamp")
        level = item.get("bodyBatteryLevel") or item.get("level")
        if ts_ms is not None and level is not None:
            readings.append(BodyBatteryReading(timestamp=_ts_to_dt(ts_ms), level=level))
    return readings


def extract_sleep_summary(target_date: date, data: dict[str, Any]) -> SleepSummary:
    dto = data.get("dailySleepDTO", data)
    score_obj = dto.get("overallSleepScore", {})
    return SleepSummary(
        date=target_date,
        total_sleep_seconds=dto.get("sleepTimeSeconds"),
        deep_sleep_seconds=dto.get("deepSleepSeconds"),
        light_sleep_seconds=dto.get("lightSleepSeconds"),
        rem_sleep_seconds=dto.get("remSleepSeconds"),
        awake_seconds=dto.get("awakeSleepSeconds"),
        sleep_score=score_obj.get("value") if isinstance(score_obj, dict) else score_obj,
        sleep_start=_ts_to_dt(dto["sleepStartTimestampGMT"]) if dto.get("sleepStartTimestampGMT") else None,
        sleep_end=_ts_to_dt(dto["sleepEndTimestampGMT"]) if dto.get("sleepEndTimestampGMT") else None,
        avg_spo2=dto.get("averageSpO2Value"),
        avg_respiration=dto.get("averageRespirationValue"),
        avg_stress=dto.get("averageStress"),
        avg_hrv=dto.get("averageHRV"),
        body_battery_change=dto.get("bodyBatteryChange"),
    )


def extract_activity(data: dict[str, Any]) -> Activity:
    return Activity(
        activity_id=str(data["activityId"]),
        activity_type=data.get("activityType", {}).get("typeKey"),
        sport=data.get("sportTypeId"),
        name=data.get("activityName"),
        start_time=_ts_to_dt(data["startTimeGMT"]) if isinstance(data.get("startTimeGMT"), (int, float)) else None,
        duration_seconds=int(data["duration"]) if data.get("duration") else None,
        elapsed_seconds=int(data["elapsedDuration"]) if data.get("elapsedDuration") else None,
        distance_meters=data.get("distance"),
        calories=data.get("calories"),
        avg_heart_rate=data.get("averageHR"),
        max_heart_rate=data.get("maxHR"),
        avg_speed=data.get("averageSpeed"),
        max_speed=data.get("maxSpeed"),
        elevation_gain=data.get("elevationGain"),
        elevation_loss=data.get("elevationLoss"),
        avg_cadence=data.get("averageRunningCadenceInStepsPerMinute"),
        avg_power=data.get("avgPower"),
        training_effect_aerobic=data.get("aerobicTrainingEffect"),
        training_effect_anaerobic=data.get("anaerobicTrainingEffect"),
        vo2max=data.get("vO2MaxValue"),
    )


def extract_hrv_summary(target_date: date, data: dict[str, Any]) -> HRVSummary:
    return HRVSummary(
        date=target_date,
        weekly_avg=data.get("weeklyAvg"),
        last_night_avg=data.get("lastNightAvg"),
        last_night_5min_high=data.get("lastNight5MinHigh"),
        baseline_low=data.get("baselineLowUpper"),
        baseline_high=data.get("baselineBalancedUpper"),
        status=data.get("status"),
    )


def extract_training_readiness(target_date: date, data: dict[str, Any]) -> TrainingReadiness:
    return TrainingReadiness(
        date=target_date,
        score=data.get("score"),
        level=data.get("level"),
        sleep_score=data.get("sleepScore"),
        recovery_score=data.get("recoveryScore"),
        hrv_score=data.get("hrvScore"),
    )
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_extractors.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/garminconnect/sync/ tests/test_extractors.py tests/fixtures/
git commit -m "feat: data extractors to transform raw Garmin JSON into SQLAlchemy models"
```

---

## Task 7: Sync Pipeline

**Files:**
- Create: `src/garminconnect/sync/pipeline.py`
- Create: `tests/test_sync_pipeline.py`

- [ ] **Step 1: Write failing test for sync pipeline**

```python
# tests/test_sync_pipeline.py
from datetime import date
from unittest.mock import MagicMock, patch

from garminconnect.sync.pipeline import SyncPipeline


def test_sync_single_date():
    mock_api = MagicMock()
    mock_repo = MagicMock()
    mock_repo.get_sync_status.return_value = None  # not yet synced

    mock_api.fetch.return_value = {"totalSteps": 8000}

    pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
    pipeline.sync_date(date(2026, 3, 17), endpoints=["daily_summary"])

    mock_api.fetch.assert_called_once()
    mock_repo.store_raw.assert_called_once()
    mock_repo.upsert.assert_called_once()
    mock_repo.mark_synced.assert_called_once()


def test_sync_skips_already_completed():
    mock_api = MagicMock()
    mock_repo = MagicMock()
    mock_repo.get_sync_status.return_value = "completed"

    pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
    pipeline.sync_date(date(2026, 3, 17), endpoints=["daily_summary"])

    mock_api.fetch.assert_not_called()


def test_sync_marks_failed_on_error():
    mock_api = MagicMock()
    mock_api.fetch.side_effect = Exception("API error")
    mock_repo = MagicMock()
    mock_repo.get_sync_status.return_value = None

    pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
    pipeline.sync_date(date(2026, 3, 17), endpoints=["daily_summary"])

    mock_repo.mark_synced.assert_called_once()
    call_kwargs = mock_repo.mark_synced.call_args
    assert call_kwargs.kwargs.get("error") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sync_pipeline.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement sync pipeline**

```python
# src/garminconnect/sync/pipeline.py
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import structlog

from garminconnect.api.client import GarminAPIClient
from garminconnect.db.repository import HealthRepository
from garminconnect.sync.extractors import (
    extract_activity,
    extract_body_battery_readings,
    extract_daily_summary,
    extract_heart_rate_readings,
    extract_hrv_summary,
    extract_sleep_summary,
    extract_stress_readings,
    extract_training_readiness,
)

logger = structlog.get_logger()

# Maps endpoint names to their extractor functions
EXTRACTORS: dict[str, Any] = {
    "daily_summary": lambda d, data: [extract_daily_summary(d, data)],
    "heart_rate": lambda d, data: extract_heart_rate_readings(data),
    "stress": lambda d, data: extract_stress_readings(data),
    "body_battery": lambda d, data: extract_body_battery_readings(data),
    "sleep": lambda d, data: [extract_sleep_summary(d, data)],
    "hrv": lambda d, data: [extract_hrv_summary(d, data)],
    "training_readiness": lambda d, data: [extract_training_readiness(d, data)],
}

# Endpoints that are date-based and should be synced daily
DAILY_SYNC_ENDPOINTS = [
    "daily_summary",
    "heart_rate",
    "stress",
    "body_battery",
    "sleep",
    "hrv",
    "training_readiness",
    "respiration",
    "spo2",
]


class SyncPipeline:
    """Orchestrates fetching from Garmin API, storing raw data, and extracting processed data."""

    def __init__(self, api_client: GarminAPIClient, repository: HealthRepository):
        self.api = api_client
        self.repo = repository

    def sync_date(
        self,
        target_date: date,
        endpoints: list[str] | None = None,
        force: bool = False,
    ) -> dict[str, str]:
        """Sync all endpoints for a given date. Returns status per endpoint."""
        results: dict[str, str] = {}
        for endpoint_name in endpoints or DAILY_SYNC_ENDPOINTS:
            if not force and self.repo.get_sync_status(endpoint_name, target_date) == "completed":
                results[endpoint_name] = "skipped"
                logger.debug("skipping_completed", endpoint=endpoint_name, date=target_date.isoformat())
                continue
            try:
                raw_data = self.api.fetch(endpoint_name, date=target_date)
                self.repo.store_raw(endpoint_name, target_date, raw_data)
                extractor = EXTRACTORS.get(endpoint_name)
                if extractor and raw_data:
                    models = extractor(target_date, raw_data)
                    if models:
                        self.repo.upsert_many(models) if isinstance(models, list) else self.repo.upsert(models)
                self.repo.mark_synced(endpoint_name, target_date)
                results[endpoint_name] = "completed"
                logger.info("synced", endpoint=endpoint_name, date=target_date.isoformat())
            except Exception as e:
                self.repo.mark_synced(endpoint_name, target_date, error=str(e))
                results[endpoint_name] = "failed"
                logger.error("sync_failed", endpoint=endpoint_name, date=target_date.isoformat(), error=str(e))
        return results

    def sync_range(
        self,
        start_date: date,
        end_date: date,
        endpoints: list[str] | None = None,
        force: bool = False,
    ) -> None:
        """Sync a date range, day by day."""
        current = start_date
        while current <= end_date:
            self.sync_date(current, endpoints=endpoints, force=force)
            current += timedelta(days=1)

    def sync_activities(self, limit: int = 20, start: int = 0) -> list[str]:
        """Sync recent activities. Returns list of synced activity IDs."""
        synced_ids = []
        try:
            raw_list = self.api.fetch(
                "activity_list",
                params={"limit": limit, "start": start},
            )
            if not raw_list:
                return synced_ids
            activities = raw_list if isinstance(raw_list, list) else raw_list.get("activities", raw_list)
            for activity_data in activities:
                activity_id = str(activity_data.get("activityId", ""))
                if not activity_id:
                    continue
                self.repo.store_raw("activity", date.today(), activity_data)
                activity = extract_activity(activity_data)
                self.repo.upsert(activity)
                synced_ids.append(activity_id)
        except Exception as e:
            logger.error("activity_sync_failed", error=str(e))
        return synced_ids
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_sync_pipeline.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/garminconnect/sync/pipeline.py tests/test_sync_pipeline.py
git commit -m "feat: sync pipeline with raw storage, extraction, and idempotent sync tracking"
```

---

## Task 8: Polling Scheduler (Daemon Mode)

**Files:**
- Create: `src/garminconnect/sync/scheduler.py`
- Create: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_scheduler.py
from unittest.mock import MagicMock, patch
from garminconnect.sync.scheduler import GarminScheduler


def test_scheduler_creates_jobs():
    mock_pipeline = MagicMock()
    scheduler = GarminScheduler(pipeline=mock_pipeline, interval_minutes=10)
    assert scheduler.interval_minutes == 10
    assert scheduler.pipeline is mock_pipeline


def test_scheduler_run_once_calls_sync():
    mock_pipeline = MagicMock()
    scheduler = GarminScheduler(pipeline=mock_pipeline, interval_minutes=10)
    scheduler.run_once()
    mock_pipeline.sync_date.assert_called()
    mock_pipeline.sync_activities.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scheduler.py -v`
Expected: FAIL

- [ ] **Step 3: Implement scheduler**

```python
# src/garminconnect/sync/scheduler.py
from __future__ import annotations

from datetime import date, timedelta

import structlog
from apscheduler.schedulers.blocking import BlockingScheduler

from garminconnect.sync.pipeline import SyncPipeline

logger = structlog.get_logger()


class GarminScheduler:
    """Polls Garmin Connect on a schedule."""

    def __init__(self, pipeline: SyncPipeline, interval_minutes: int = 10):
        self.pipeline = pipeline
        self.interval_minutes = interval_minutes

    def run_once(self) -> None:
        """Run a single sync cycle: today + yesterday (for late-arriving data)."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        logger.info("sync_cycle_start")
        self.pipeline.sync_date(yesterday)
        self.pipeline.sync_date(today, force=True)  # Always re-sync today
        self.pipeline.sync_activities(limit=10)
        logger.info("sync_cycle_complete")

    def start(self) -> None:
        """Start the blocking scheduler loop."""
        logger.info("scheduler_starting", interval_minutes=self.interval_minutes)
        self.run_once()  # Run immediately on startup
        scheduler = BlockingScheduler()
        scheduler.add_job(
            self.run_once,
            "interval",
            minutes=self.interval_minutes,
            id="garmin_sync",
        )
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("scheduler_stopped")
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_scheduler.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/garminconnect/sync/scheduler.py tests/test_scheduler.py
git commit -m "feat: APScheduler-based polling daemon with configurable interval"
```

---

## Task 9: MCP Server (PostgreSQL-backed)

**Files:**
- Create: `src/garminconnect/mcp/__init__.py`
- Create: `src/garminconnect/mcp/server.py`
- Create: `src/garminconnect/mcp/tools.py`
- Create: `tests/test_mcp_server.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_mcp_server.py
from garminconnect.mcp.server import create_mcp_server


def test_mcp_server_creates():
    server = create_mcp_server(postgres_url="postgresql://test:test@localhost/test")
    assert server is not None
    assert server.name == "Garmin Health Data"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mcp_server.py -v`
Expected: FAIL

- [ ] **Step 3: Implement MCP server**

```python
# src/garminconnect/mcp/__init__.py
from garminconnect.mcp.server import create_mcp_server

__all__ = ["create_mcp_server"]
```

```python
# src/garminconnect/mcp/tools.py
"""SQL query helpers for MCP tools."""
from __future__ import annotations

from datetime import date, timedelta

# Pre-built queries that LLMs can use
QUERY_TEMPLATES = {
    "daily_overview": """
        SELECT date, total_steps, total_calories, resting_heart_rate,
               avg_stress, body_battery_high, avg_spo2
        FROM daily_summary
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "sleep_trend": """
        SELECT date, total_sleep_seconds / 3600.0 AS hours_slept,
               deep_sleep_seconds / 3600.0 AS deep_hours,
               rem_sleep_seconds / 3600.0 AS rem_hours,
               sleep_score
        FROM sleep_summary
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "hr_intraday": """
        SELECT timestamp, heart_rate
        FROM heart_rate
        WHERE timestamp >= :start AND timestamp < :end
        ORDER BY timestamp
    """,
    "activity_list": """
        SELECT activity_id, activity_type, name, start_time,
               duration_seconds / 60.0 AS duration_min,
               distance_meters / 1000.0 AS distance_km,
               avg_heart_rate, calories
        FROM activities
        ORDER BY start_time DESC
        LIMIT :limit
    """,
    "training_readiness_trend": """
        SELECT date, score, level, sleep_score, recovery_score, hrv_score
        FROM training_readiness
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "hrv_trend": """
        SELECT date, weekly_avg, last_night_avg, status
        FROM hrv
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "body_composition_trend": """
        SELECT date, weight_kg, body_fat_pct, muscle_mass_kg
        FROM body_composition
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "stress_intraday": """
        SELECT timestamp, stress_level
        FROM stress
        WHERE timestamp >= :start AND timestamp < :end
        ORDER BY timestamp
    """,
}


def get_table_list() -> list[str]:
    return [
        "daily_summary",
        "body_composition",
        "heart_rate",
        "stress",
        "body_battery",
        "spo2",
        "respiration",
        "sleep_summary",
        "sleep_stages",
        "activities",
        "activity_trackpoints",
        "hrv",
        "training_readiness",
        "training_status",
        "race_predictions",
        "sync_status",
    ]
```

```python
# src/garminconnect/mcp/server.py
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
                text(
                    "SELECT column_name, data_type "
                    "FROM information_schema.columns "
                    "WHERE table_name = :table "
                    "ORDER BY ordinal_position"
                ),
                {"table": table_name},
            ).fetchall()
            return {row[0]: row[1] for row in rows}

    @mcp.tool()
    def query_health_data(query_name: str, start_date: str = "", end_date: str = "", limit: int = 30) -> list[dict]:
        """Run a pre-built health data query.

        Available queries: daily_overview, sleep_trend, hr_intraday, activity_list,
        training_readiness_trend, hrv_trend, body_composition_trend, stress_intraday.

        Dates in YYYY-MM-DD format. Defaults to last 7 days.
        """
        template = QUERY_TEMPLATES.get(query_name)
        if not template:
            return [{"error": f"Unknown query. Available: {list(QUERY_TEMPLATES.keys())}"}]
        end = date.fromisoformat(end_date) if end_date else date.today()
        start = date.fromisoformat(start_date) if start_date else end - timedelta(days=7)
        with engine.connect() as conn:
            result = conn.execute(
                text(template),
                {"start": start.isoformat(), "end": end.isoformat(), "limit": limit},
            )
            return [dict(row._mapping) for row in result.fetchall()]

    @mcp.tool()
    def execute_sql(query: str) -> list[dict]:
        """Execute a read-only SQL query against the health database.

        Only SELECT statements are allowed. Use this for custom queries
        not covered by query_health_data.
        """
        normalized = query.strip().upper()
        if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
            return [{"error": "Only SELECT/WITH queries are allowed"}]
        for forbidden in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"]:
            if forbidden in normalized.split():
                return [{"error": f"Forbidden keyword: {forbidden}"}]
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            result = conn.execute(text(query))
            rows = result.fetchmany(500)
            return [dict(row._mapping) for row in rows]

    @mcp.tool()
    def get_health_summary(days: int = 7) -> dict[str, Any]:
        """Get a comprehensive health summary for the last N days."""
        end = date.today()
        start = end - timedelta(days=days)
        summary: dict[str, Any] = {}
        with engine.connect() as conn:
            # Daily averages
            row = conn.execute(
                text(
                    "SELECT AVG(total_steps) AS avg_steps, AVG(total_calories) AS avg_calories, "
                    "AVG(resting_heart_rate) AS avg_rhr, AVG(avg_stress) AS avg_stress, "
                    "AVG(avg_spo2) AS avg_spo2 "
                    "FROM daily_summary WHERE date BETWEEN :s AND :e"
                ),
                {"s": start.isoformat(), "e": end.isoformat()},
            ).fetchone()
            if row:
                summary["daily_averages"] = dict(row._mapping)
            # Sleep averages
            row = conn.execute(
                text(
                    "SELECT AVG(total_sleep_seconds)/3600.0 AS avg_sleep_hours, "
                    "AVG(sleep_score) AS avg_sleep_score "
                    "FROM sleep_summary WHERE date BETWEEN :s AND :e"
                ),
                {"s": start.isoformat(), "e": end.isoformat()},
            ).fetchone()
            if row:
                summary["sleep_averages"] = dict(row._mapping)
            # Activity count
            row = conn.execute(
                text(
                    "SELECT COUNT(*) AS count, SUM(distance_meters)/1000.0 AS total_km, "
                    "SUM(calories) AS total_calories "
                    "FROM activities WHERE start_time >= :s"
                ),
                {"s": start.isoformat()},
            ).fetchone()
            if row:
                summary["activities"] = dict(row._mapping)
        return summary

    @mcp.tool()
    def get_sync_status() -> list[dict]:
        """Check the sync status — when was each metric last synced?"""
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT metric_name, MAX(date) AS last_date, "
                    "COUNT(*) FILTER (WHERE status = 'completed') AS completed, "
                    "COUNT(*) FILTER (WHERE status = 'failed') AS failed "
                    "FROM sync_status GROUP BY metric_name ORDER BY metric_name"
                )
            ).fetchall()
            return [dict(zip(["metric", "last_date", "completed", "failed"], row)) for row in rows]

    return mcp
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_mcp_server.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add src/garminconnect/mcp/ tests/test_mcp_server.py
git commit -m "feat: MCP server with 6 tools for health data querying via PostgreSQL"
```

---

## Task 10: CLI Commands

**Files:**
- Create: `src/garminconnect/cli/__init__.py`
- Create: `src/garminconnect/cli/commands.py`
- Create: `src/garminconnect/__main__.py`

- [ ] **Step 1: Implement CLI**

```python
# src/garminconnect/cli/__init__.py
"""CLI commands for garmin-server."""

# src/garminconnect/cli/commands.py
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
    from garminconnect.auth.client import GarminAuth
    from garminconnect.api.client import GarminAPIClient
    from garminconnect.db import create_engine_and_tables, get_mongo_db, HealthRepository
    from garminconnect.sync.pipeline import SyncPipeline

    auth = GarminAuth(token_dir=settings.garmin_token_dir)
    auth.ensure_authenticated(settings.garmin_email, settings.garmin_password)

    _, session_factory = create_engine_and_tables()
    mongo_db = get_mongo_db()
    repo = HealthRepository(session_factory=session_factory, mongo_db=mongo_db)
    api = GarminAPIClient(auth=auth)

    pipeline = SyncPipeline(api_client=api, repository=repo)
    end = date.today()
    start = end - timedelta(days=days)
    click.echo(f"Backfilling {days} days: {start} to {end}")
    pipeline.sync_range(start, end, force=force)
    click.echo("Backfill complete.")


@cli.command()
def daemon() -> None:
    """Start the polling daemon."""
    import logging

    from garminconnect.auth.client import GarminAuth
    from garminconnect.api.client import GarminAPIClient
    from garminconnect.db import create_engine_and_tables, get_mongo_db, HealthRepository
    from garminconnect.sync.pipeline import SyncPipeline
    from garminconnect.sync.scheduler import GarminScheduler

    auth = GarminAuth(token_dir=settings.garmin_token_dir)
    auth.ensure_authenticated(settings.garmin_email, settings.garmin_password)

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
    from garminconnect.auth.client import GarminAuth

    email = click.prompt("Garmin email", default=settings.garmin_email)
    password = click.prompt("Garmin password", hide_input=True)
    auth = GarminAuth(token_dir=settings.garmin_token_dir)
    auth.login(email, password)
    click.echo(f"Logged in. Tokens saved to {settings.garmin_token_dir}")


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
```

```python
# src/garminconnect/__main__.py
from garminconnect.cli.commands import cli

if __name__ == "__main__":
    cli()
```

- [ ] **Step 2: Run CLI help to verify it works**

Run: `cd /home/alx/CODE/0x2alx_github/garminconnectconnect && pip install -e . && garmin-server --help`
Expected: Shows available commands (backfill, daemon, mcp, login, status)

- [ ] **Step 3: Commit**

```bash
git add src/garminconnect/cli/ src/garminconnect/__main__.py
git commit -m "feat: CLI with backfill, daemon, mcp, login, and status commands"
```

---

## Task 11: Alembic Migrations

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: initial migration in `alembic/versions/`

- [ ] **Step 1: Initialize alembic**

Run: `cd /home/alx/CODE/0x2alx_github/garminconnectconnect && alembic init alembic`

- [ ] **Step 2: Configure `alembic/env.py` to use our models**

Edit `alembic/env.py` to import `garminconnect.models.base.Base` as `target_metadata` and read `settings.postgres_url` for the database URL.

- [ ] **Step 3: Generate initial migration**

Run: `alembic revision --autogenerate -m "initial schema"`

- [ ] **Step 4: Verify migration applies**

Run: `docker compose up -d timescaledb && sleep 5 && alembic upgrade head`
Expected: All tables created

- [ ] **Step 5: Commit**

```bash
git add alembic.ini alembic/
git commit -m "feat: Alembic migrations for database schema management"
```

---

## Task 12: Integration Test with Docker

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
"""Integration test using testcontainers — requires Docker."""
import pytest
from datetime import date

try:
    from testcontainers.postgres import PostgresContainer
    from testcontainers.mongodb import MongoDbContainer
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False

from garminconnect.db.postgres import create_engine_and_tables
from garminconnect.db.mongo import get_mongo_db
from garminconnect.db.repository import HealthRepository
from garminconnect.models.daily import DailySummary


@pytest.mark.skipif(not HAS_DOCKER, reason="testcontainers not installed")
def test_full_upsert_and_read():
    with PostgresContainer("timescale/timescaledb:latest-pg16") as pg:
        url = pg.get_connection_url().replace("psycopg2", "psycopg")
        engine, session_factory = create_engine_and_tables(url=url)
        repo = HealthRepository(session_factory=session_factory)

        summary = DailySummary(
            date=date(2026, 3, 17),
            total_steps=8000,
            total_calories=2100,
            resting_heart_rate=58,
        )
        repo.upsert(summary)

        session = session_factory()
        result = session.get(DailySummary, date(2026, 3, 17))
        assert result is not None
        assert result.total_steps == 8000
        session.close()


@pytest.mark.skipif(not HAS_DOCKER, reason="testcontainers not installed")
def test_raw_storage_in_mongo():
    with MongoDbContainer("mongo:7") as mongo:
        db = get_mongo_db(url=mongo.get_connection_url(), db_name="test_raw")
        repo = HealthRepository(session_factory=lambda: None, mongo_db=db)
        repo.store_raw("daily_summary", date(2026, 3, 17), {"totalSteps": 8000})
        doc = db["raw_daily_summary"].find_one({"date": "2026-03-17"})
        assert doc is not None
        assert doc["data"]["totalSteps"] == 8000
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: 2 passed (or skipped if Docker unavailable)

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration tests with testcontainers (TimescaleDB + MongoDB)"
```

---

## Task 13: MCP Server Configuration for Claude Code

**Files:**
- Modify: User-level Claude Code settings

- [ ] **Step 1: Add MCP server config**

After the server is running, add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "garmin-health": {
      "command": "garmin-server",
      "args": ["mcp"],
      "env": {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "garmin",
        "POSTGRES_USER": "garmin",
        "POSTGRES_PASSWORD": "garmin_secret"
      }
    }
  }
}
```

- [ ] **Step 2: Verify MCP server connects**

Run: `/mcp` in Claude Code
Expected: `garmin-health` server shows as connected with 6 tools

- [ ] **Step 3: Commit any config changes**

```bash
git commit -m "docs: MCP server configuration for Claude Code"
```

---

## Execution Order Summary

| Task | Component | Dependencies | Est. Steps |
|------|-----------|-------------|-----------|
| 1 | Project scaffolding + Docker | None | 7 |
| 2 | Auth layer (garth) | Task 1 | 5 |
| 3 | API client + endpoints | Task 2 | 5 |
| 4 | SQLAlchemy models | Task 1 | 6 |
| 5 | DB layer (Postgres + Mongo) | Tasks 1, 4 | 5 |
| 6 | Data extractors | Tasks 4 | 6 |
| 7 | Sync pipeline | Tasks 3, 5, 6 | 5 |
| 8 | Polling scheduler | Task 7 | 5 |
| 9 | MCP server | Tasks 4, 5 | 5 |
| 10 | CLI commands | Tasks 2, 7, 8, 9 | 3 |
| 11 | Alembic migrations | Tasks 4, 5 | 5 |
| 12 | Integration tests | Tasks 5, 7 | 3 |
| 13 | MCP config for Claude Code | Task 9 | 3 |

**Parallelizable:** Tasks 2-3 (auth+API) and Tasks 4-6 (models+DB+extractors) can run in parallel. Task 9 (MCP) can be built in parallel with Tasks 7-8 (sync+scheduler).
