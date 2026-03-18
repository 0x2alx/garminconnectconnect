from __future__ import annotations
from datetime import date, timedelta
from typing import Any
import structlog
from garminconnect.api.client import GarminAPIClient
from garminconnect.db.repository import HealthRepository
from garminconnect.sync.extractors import (
    _parse_garmin_timestamp,
    extract_activity, extract_body_battery_readings, extract_body_composition,
    extract_daily_summary, extract_heart_rate_readings, extract_hrv_summary,
    extract_respiration_readings, extract_sleep_summary, extract_spo2_readings,
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
    "respiration": lambda d, data: extract_respiration_readings(data),
    "spo2": lambda d, data: extract_spo2_readings(data),
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

    def sync_date(self, target_date: date, endpoints: list[str] | None = None, force: bool = False) -> dict[str, str]:
        results: dict[str, str] = {}
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

    def sync_body_composition(self, start_date: date, end_date: date) -> int:
        """Sync weight/body composition for a date range."""
        count = 0
        try:
            raw_data = self.api.fetch("weight", start=start_date, end=end_date)
            if raw_data:
                self.repo.store_raw("weight", end_date, raw_data)
                entries = extract_body_composition(end_date, raw_data)
                if entries:
                    self.repo.upsert_many(entries)
                    count = len(entries)
                    logger.info("synced_body_composition", count=count)
        except Exception as e:
            logger.error("body_composition_sync_failed", error=str(e))
        return count

    def sync_activities(self, limit: int = 20, start: int = 0, max_activities: int = 200) -> list[str]:
        synced_ids: list[str] = []
        offset = start
        try:
            while len(synced_ids) < max_activities:
                raw_list = self.api.fetch("activity_list", params={"limit": limit, "start": offset})
                if not raw_list:
                    break
                activities = raw_list if isinstance(raw_list, list) else raw_list.get("activities", raw_list)
                if not activities:
                    break
                for activity_data in activities:
                    activity_id = str(activity_data.get("activityId", ""))
                    if not activity_id:
                        continue
                    activity_date = None
                    ts = _parse_garmin_timestamp(activity_data.get("startTimeGMT") or activity_data.get("beginTimestamp"))
                    if ts:
                        activity_date = ts.date()
                    self.repo.store_raw("activity", activity_date or date.today(), activity_data)
                    activity = extract_activity(activity_data)
                    self.repo.upsert(activity)
                    synced_ids.append(activity_id)
                if len(activities) < limit:
                    break  # Last page
                offset += limit
        except Exception as e:
            logger.error("activity_sync_failed", error=str(e))
        return synced_ids
