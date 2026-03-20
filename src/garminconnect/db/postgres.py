from __future__ import annotations
import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from garminconnect.config import settings
from garminconnect.models.base import Base

logger = structlog.get_logger()
import garminconnect.models.daily
import garminconnect.models.monitoring
import garminconnect.models.sleep
import garminconnect.models.activities
import garminconnect.models.training
import garminconnect.models.sync_status

HYPERTABLES = [
    ("heart_rate", "timestamp"),
    ("stress", "timestamp"),
    ("body_battery", "timestamp"),
    ("spo2", "timestamp"),
    ("respiration", "timestamp"),
    ("sleep_stages", "timestamp"),
    ("activity_trackpoints", "timestamp"),
    ("hrv_readings", "timestamp"),
]


def create_engine_and_tables(url: str | None = None) -> tuple[Engine, sessionmaker[Session]]:
    engine = create_engine(url or settings.postgres_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
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
            except Exception as e:
                logger.warning("hypertable_creation_failed", table=table_name, error=str(e))
                conn.rollback()
    factory = sessionmaker(engine)
    return engine, factory
