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
    for entry in data.get("heartRateValues") or []:
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
    for entry in data.get("stressValuesArray") or []:
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

    bodyBatteryValuesArray entries are [epoch_ms, "MEASURED", battery_level, delta].
    """
    readings = []
    for item in data.get("bodyBatteryValuesArray") or []:
        if isinstance(item, (list, tuple)):
            # Format: [epoch_ms, status_str, battery_level, delta]
            # or possibly [epoch_ms, battery_level]
            ts_ms = item[0] if len(item) >= 1 else None
            if len(item) >= 4:
                level = item[2]  # [ts, "MEASURED", level, delta]
            elif len(item) >= 2:
                level = item[1]  # [ts, level]
            else:
                continue
        elif isinstance(item, dict):
            ts_ms = item.get("startTimestampGMT") or item.get("timestamp")
            level = item.get("bodyBatteryLevel") or item.get("level")
        else:
            continue
        if ts_ms is None or level is None:
            continue
        try:
            level_int = int(level)
        except (ValueError, TypeError):
            continue
        if level_int >= 0:
            readings.append(BodyBatteryReading(timestamp=_ts_to_dt(int(ts_ms)), level=level_int))
    return readings


def extract_respiration_readings(data: dict[str, Any]) -> list[RespirationReading]:
    """Extract from respirationValuesArray: [epoch_ms, breaths_per_min]."""
    readings = []
    for entry in data.get("respirationValuesArray") or []:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        ts_ms, rate = entry[0], entry[1]
        if ts_ms is None or rate is None:
            continue
        try:
            readings.append(RespirationReading(timestamp=_ts_to_dt(int(ts_ms)), respiration_rate=float(rate)))
        except (ValueError, TypeError):
            continue
    return readings


def extract_spo2_readings(data: dict[str, Any]) -> list[SpO2Reading]:
    """Extract SpO2 from spO2HourlyAverages or continuousReadingDTOList."""
    readings = []
    # Try hourly averages first: [[epoch_ms, value], ...]
    for entry in data.get("spO2HourlyAverages") or []:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        ts_ms, value = entry[0], entry[1]
        if value is None:
            continue
        try:
            # ts_ms might be a BSON Long object, convert via int
            readings.append(SpO2Reading(timestamp=_ts_to_dt(int(ts_ms)), spo2=float(value)))
        except (ValueError, TypeError, OSError):
            continue
    # Also try continuous readings
    for entry in data.get("continuousReadingDTOList") or []:
        if not isinstance(entry, dict):
            continue
        ts_ms = entry.get("epochTimestamp") or entry.get("startTimestampGMT")
        value = entry.get("spo2") or entry.get("reading")
        if ts_ms is None or value is None:
            continue
        try:
            readings.append(SpO2Reading(timestamp=_ts_to_dt(int(ts_ms)), spo2=float(value)))
        except (ValueError, TypeError, OSError):
            continue
    return readings


def extract_body_composition(target_date: date, data: Any) -> list[BodyComposition]:
    """Extract from weight endpoint response."""
    entries = []
    # Response can be a list of weight entries or a dict with dailyWeightSummaries
    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("dailyWeightSummaries", data.get("dateWeightList", []))
        if not items and "weight" in data:
            items = [data]
    for item in items:
        if not isinstance(item, dict):
            continue
        entry_date = item.get("date") or item.get("calendarDate")
        if entry_date and isinstance(entry_date, str):
            try:
                d = date.fromisoformat(entry_date)
            except ValueError:
                d = target_date
        else:
            d = target_date
        weight = item.get("weight")
        if weight and weight > 1000:
            weight = weight / 1000.0  # Garmin returns grams sometimes
        entries.append(BodyComposition(
            date=d,
            weight_kg=weight,
            bmi=item.get("bmi"),
            body_fat_pct=item.get("bodyFat"),
            muscle_mass_kg=item.get("muscleMass"),
            bone_mass_kg=item.get("boneMass"),
            body_water_pct=item.get("bodyWater"),
        ))
    return entries


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
    start_time = data.get("startTimeGMT")
    if isinstance(start_time, str):
        try:
            start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            start_time = None
    elif isinstance(start_time, (int, float)):
        start_time = _ts_to_dt(int(start_time))
    else:
        start_time = None

    return Activity(
        activity_id=str(data["activityId"]),
        activity_type=data.get("activityType", {}).get("typeKey") if isinstance(data.get("activityType"), dict) else data.get("activityType"),
        sport=data.get("sportTypeId"),
        name=data.get("activityName"),
        start_time=start_time,
        duration_seconds=int(float(data["duration"])) if data.get("duration") else None,
        elapsed_seconds=int(float(data["elapsedDuration"])) if data.get("elapsedDuration") else None,
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
    # HRV response may have data nested under hrvSummaries
    if isinstance(data, dict) and "hrvSummaries" in data:
        summaries = data["hrvSummaries"]
        if isinstance(summaries, list) and summaries:
            data = summaries[0]
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
