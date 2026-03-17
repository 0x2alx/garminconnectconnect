from __future__ import annotations
from datetime import date, timedelta
from typing import Any
import structlog
from garminconnect.api.client import GarminAPIClient
from garminconnect.db.repository import HealthRepository
from garminconnect.sync.extractors import (
    extract_activity, extract_body_battery_readings, extract_daily_summary,
    extract_heart_rate_readings, extract_hrv_summary, extract_sleep_summary,
    extract_stress_readings, extract_training_readiness,
)

logger = structlog.get_logger()

EXTRACTORS: dict[str, Any] = {
    "daily_summary": lambda d, data: [extract_daily_summary(d, data)],
    "heart_rate": lambda d, data: extract_heart_rate_readings(data),
    "stress": lambda d, data: extract_stress_readings(data),
    "sleep": lambda d, data: [extract_sleep_summary(d, data)],
    "hrv": lambda d, data: [extract_hrv_summary(d, data)],
    "training_readiness": lambda d, data: [extract_training_readiness(d, data)],
}

# Endpoints to sync daily. body_battery is extracted from the stress response.
DAILY_SYNC_ENDPOINTS = [
    "daily_summary", "heart_rate", "stress",
    "sleep", "hrv", "training_readiness", "respiration", "spo2",
]


class SyncPipeline:
    def __init__(self, api_client: GarminAPIClient, repository: HealthRepository):
        self.api = api_client
        self.repo = repository
        self._stress_cache: dict[str, Any] = {}

    def sync_date(self, target_date: date, endpoints: list[str] | None = None, force: bool = False) -> dict[str, str]:
        results: dict[str, str] = {}
        self._stress_cache.clear()
        for endpoint_name in endpoints or DAILY_SYNC_ENDPOINTS:
            if not force and self.repo.get_sync_status(endpoint_name, target_date) == "completed":
                results[endpoint_name] = "skipped"
                logger.debug("skipping_completed", endpoint=endpoint_name, date=target_date.isoformat())
                continue
            try:
                raw_data = self.api.fetch(endpoint_name, date=target_date)
                self.repo.store_raw(endpoint_name, target_date, raw_data)

                # Extract body battery from stress response (same endpoint)
                if endpoint_name == "stress" and raw_data:
                    self._stress_cache[target_date.isoformat()] = raw_data
                    bb_readings = extract_body_battery_readings(raw_data)
                    if bb_readings:
                        self.repo.upsert_many(bb_readings)

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

    def sync_range(self, start_date: date, end_date: date, endpoints: list[str] | None = None, force: bool = False) -> None:
        current = start_date
        while current <= end_date:
            self.sync_date(current, endpoints=endpoints, force=force)
            current += timedelta(days=1)

    def sync_activities(self, limit: int = 20, start: int = 0) -> list[str]:
        synced_ids = []
        try:
            raw_list = self.api.fetch("activity_list", params={"limit": limit, "start": start})
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
