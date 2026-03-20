from __future__ import annotations
import logging
from datetime import date, timedelta
from typing import Any
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
from garminconnect.api.client import GarminAPIClient
from garminconnect.db.repository import HealthRepository
from garminconnect.sync.extractors import (
    _parse_garmin_timestamp,
    extract_activity, extract_badges, extract_blood_pressure_readings,
    extract_body_battery_events, extract_body_battery_readings, extract_body_composition,
    extract_daily_summary, extract_floors_readings, extract_heart_rate_readings,
    extract_hrv_summary, extract_intensity_minutes_readings, extract_personal_records,
    extract_respiration_readings, extract_running_tolerance, extract_sleep_summary,
    extract_sleep_stages, extract_spo2_readings, extract_stress_readings,
    extract_training_plan, extract_training_readiness, extract_workouts,
    extract_scheduled_workouts, extract_trackpoints,
)

logger = structlog.get_logger()

EXTRACTORS: dict[str, Any] = {
    "daily_summary": lambda d, data: [extract_daily_summary(d, data)],
    "heart_rate": lambda d, data: extract_heart_rate_readings(data),
    "stress": lambda d, data: extract_stress_readings(data),
    "sleep": lambda d, data: [extract_sleep_summary(d, data)] + extract_sleep_stages(data),
    "hrv": lambda d, data: [extract_hrv_summary(d, data)],
    "training_readiness": lambda d, data: [extract_training_readiness(d, data)],
    "respiration": lambda d, data: extract_respiration_readings(data),
    "spo2": lambda d, data: extract_spo2_readings(data),
    "body_battery_events": lambda d, data: extract_body_battery_events(data),
    "intensity_minutes": lambda d, data: extract_intensity_minutes_readings(data),
    "floors": lambda d, data: extract_floors_readings(data),
    "blood_pressure": lambda d, data: extract_blood_pressure_readings(data),
}

# Endpoints to sync daily. body_battery is extracted from the stress response.
DAILY_SYNC_ENDPOINTS = [
    "daily_summary", "heart_rate", "stress",
    "sleep", "hrv", "training_readiness", "respiration", "spo2",
    "body_battery_events", "intensity_minutes", "floors",
    "blood_pressure",
]


_retry_logger = logging.getLogger("garminconnect.sync.pipeline")


class SyncPipeline:
    def __init__(self, api_client: GarminAPIClient, repository: HealthRepository):
        self.api = api_client
        self.repo = repository

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=5, max=120),
        before_sleep=before_sleep_log(_retry_logger, logging.WARNING),
        reraise=True,
    )
    def _fetch_with_retry(self, endpoint_name: str, **kwargs: Any) -> Any:
        """Fetch from the Garmin API with exponential-backoff retry."""
        return self.api.fetch(endpoint_name, **kwargs)

    def sync_date(self, target_date: date, endpoints: list[str] | None = None, force: bool = False) -> dict[str, str]:
        results: dict[str, str] = {}
        for endpoint_name in endpoints or DAILY_SYNC_ENDPOINTS:
            if not force and self.repo.get_sync_status(endpoint_name, target_date) == "completed":
                results[endpoint_name] = "skipped"
                logger.debug("skipping_completed", endpoint=endpoint_name, date=target_date.isoformat())
                continue
            try:
                raw_data = self._fetch_with_retry(endpoint_name, date=target_date)
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
            raw_data = self._fetch_with_retry("weight", start=start_date, end=end_date)
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
                raw_list = self._fetch_with_retry("activity_list", params={"limit": limit, "start": offset})
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
            if synced_ids:
                self.sync_activity_details(synced_ids)
        except Exception as e:
            logger.error("activity_sync_failed", error=str(e))
        return synced_ids

    def sync_activity_details(self, activity_ids: list[str]) -> int:
        """Fetch GPS/detail data for activities and extract trackpoints."""
        count = 0
        for activity_id in activity_ids:
            try:
                raw_data = self._fetch_with_retry(
                    "activity_gps", activity_id=activity_id,
                    params={"maxChartSize": 10000, "maxPolylineSize": 10000},
                )
                if raw_data:
                    self.repo.store_raw("activity_gps", date.today(), raw_data)
                    trackpoints = extract_trackpoints(activity_id, raw_data)
                    if trackpoints:
                        self.repo.upsert_many(trackpoints)
                        count += len(trackpoints)
                        logger.info("synced_trackpoints", activity_id=activity_id, count=len(trackpoints))
            except Exception as e:
                logger.error("trackpoint_sync_failed", activity_id=activity_id, error=str(e))
        return count

    def sync_running_tolerance(self) -> bool:
        """Sync running tolerance stats (dateless endpoint)."""
        try:
            raw_data = self._fetch_with_retry("running_tolerance")
            if raw_data:
                self.repo.store_raw("running_tolerance", date.today(), raw_data)
                rt = extract_running_tolerance(date.today(), raw_data)
                self.repo.upsert(rt)
                logger.info("synced_running_tolerance")
                return True
        except Exception as e:
            logger.error("running_tolerance_sync_failed", error=str(e))
        return False

    def sync_workouts(self) -> list[str]:
        """Sync all workouts from Garmin Connect."""
        synced_ids: list[str] = []
        try:
            raw_data = self._fetch_with_retry("workout_list")
            if raw_data:
                self.repo.store_raw("workouts", date.today(), raw_data)
                workouts = extract_workouts(raw_data)
                if workouts:
                    self.repo.upsert_many(workouts)
                    synced_ids = [w.workout_id for w in workouts]
                    logger.info("synced_workouts", count=len(synced_ids))
        except Exception as e:
            logger.error("workout_sync_failed", error=str(e))
        return synced_ids

    def sync_personal_records(self) -> int:
        """Sync personal records from Garmin Connect."""
        count = 0
        try:
            raw_data = self._fetch_with_retry("personal_records")
            if raw_data:
                self.repo.store_raw("personal_records", date.today(), raw_data)
                records = extract_personal_records(raw_data)
                if records:
                    self.repo.upsert_many(records)
                    count = len(records)
                    logger.info("synced_personal_records", count=count)
        except Exception as e:
            logger.error("personal_records_sync_failed", error=str(e))
        return count

    def sync_badges(self) -> int:
        """Sync earned badges from Garmin Connect."""
        count = 0
        try:
            raw_data = self._fetch_with_retry("badges")
            if raw_data:
                self.repo.store_raw("badges", date.today(), raw_data)
                badges = extract_badges(raw_data)
                if badges:
                    self.repo.upsert_many(badges)
                    count = len(badges)
                    logger.info("synced_badges", count=count)
        except Exception as e:
            logger.error("badge_sync_failed", error=str(e))
        return count

    def sync_training_plan(self) -> str | None:
        """Sync active training plan from Garmin Connect."""
        try:
            raw_data = self._fetch_with_retry("training_plan")
            if raw_data:
                self.repo.store_raw("training_plan", date.today(), raw_data)
                plan = extract_training_plan(raw_data)
                self.repo.upsert(plan)
                logger.info("synced_training_plan", plan_id=plan.plan_id)
                return plan.plan_id
        except Exception as e:
            logger.error("training_plan_sync_failed", error=str(e))
        return None

    def sync_calendar(self, year: int | None = None, month: int | None = None) -> int:
        """Sync scheduled workouts from the Garmin calendar.

        When called without arguments, syncs a 7-month window: 3 months back,
        current month, and 3 months forward. This captures past scheduled
        workouts and future training plan changes.

        When called with explicit year/month, syncs just that month.
        """
        today = date.today()
        if year is not None and month is not None:
            months_to_sync = [(year, month)]
        else:
            months_to_sync = []
            for offset in range(-3, 4):
                d = today.replace(day=1)
                # Shift by offset months
                m = d.month + offset
                y = d.year
                while m < 1:
                    m += 12
                    y -= 1
                while m > 12:
                    m -= 12
                    y += 1
                months_to_sync.append((y, m))
        count = 0
        for y, m in months_to_sync:
            try:
                raw_data = self._fetch_with_retry("calendar", year=y, month=m)
                if raw_data:
                    self.repo.store_raw("calendar", today, raw_data)
                    items = extract_scheduled_workouts(raw_data)
                    if items:
                        self.repo.upsert_many(items)
                        count += len(items)
                        logger.info("synced_calendar", year=y, month=m, count=len(items))
            except Exception as e:
                logger.error("calendar_sync_failed", year=y, month=m, error=str(e))
        return count
