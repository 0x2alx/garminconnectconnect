"""Integration test using testcontainers - requires Docker."""
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
