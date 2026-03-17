"""Transform raw Garmin API JSON responses into SQLAlchemy model instances."""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Any
from garminconnect.models.daily import DailySummary, BodyComposition
from garminconnect.models.monitoring import (
    BodyBatteryReading, HeartRateReading, RespirationReading, SpO2Reading, StressReading,
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
    for entry in data.get("heartRateValues", []):
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        ts_ms, hr = entry[0], entry[1]
        if ts_ms is None or hr is None:
            continue
        try:
            readings.append(HeartRateReading(timestamp=_ts_to_dt(int(ts_ms)), heart_rate=int(hr)))
        except (ValueError, TypeError):
            continue
    return readings


def extract_stress_readings(data: dict[str, Any]) -> list[StressReading]:
    readings = []
    for entry in data.get("stressValuesArray", []):
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        ts_ms, level = entry[0], entry[1]
        if ts_ms is None or level is None:
            continue
        try:
            level = int(level)
        except (ValueError, TypeError):
            continue
        if level >= 0:
            readings.append(StressReading(timestamp=_ts_to_dt(int(ts_ms)), stress_level=level))
    return readings


def extract_body_battery_readings(data: dict[str, Any]) -> list[BodyBatteryReading]:
    """Extract body battery from the stress endpoint response.

    bodyBatteryValuesArray entries are [epoch_ms, battery_level] arrays.
    """
    readings = []
    for item in data.get("bodyBatteryValuesArray", []):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            ts_ms, level = item[0], item[1]
        elif isinstance(item, dict):
            ts_ms = item.get("startTimestampGMT") or item.get("timestamp")
            level = item.get("bodyBatteryLevel") or item.get("level")
        else:
            continue
        if ts_ms is None or level is None:
            continue
        try:
            readings.append(BodyBatteryReading(timestamp=_ts_to_dt(int(ts_ms)), level=int(level)))
        except (ValueError, TypeError):
            continue
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


def extract_training_readiness(target_date: date, data: Any) -> TrainingReadiness:
    # API returns a list of readiness snapshots; pick the morning reading or first entry
    if isinstance(data, list):
        entry = next(
            (e for e in data if e.get("inputContext") == "AFTER_WAKEUP_RESET"),
            data[0] if data else {},
        )
    else:
        entry = data
    return TrainingReadiness(
        date=target_date,
        score=entry.get("score"),
        level=entry.get("level"),
        sleep_score=entry.get("sleepScore"),
        recovery_score=entry.get("recoveryScore"),
        hrv_score=entry.get("hrvScore"),
    )
