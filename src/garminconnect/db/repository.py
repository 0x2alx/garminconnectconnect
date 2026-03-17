from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Any, Callable
from sqlalchemy.orm import Session
from pymongo.database import Database
import structlog
from garminconnect.models.base import Base

logger = structlog.get_logger()


class HealthRepository:
    def __init__(self, session_factory: Callable[[], Session], mongo_db: Database | None = None):
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
