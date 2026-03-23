"""Transform raw Garmin API JSON responses into SQLAlchemy model instances."""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Any
from garminconnect.models.daily import DailySummary, BodyComposition, Hydration
from garminconnect.models.monitoring import (
    BodyBatteryReading, HeartRateReading, HRVReading, RespirationReading, SpO2Reading,
    StressReading, BodyBatteryEvent, IntensityMinutesReading, FloorsReading, BloodPressureReading,
)
from garminconnect.models.sleep import SleepSummary, SleepStage
from garminconnect.models.activities import Activity, ActivityTrackpoint
from garminconnect.models.training import (
    HRVSummary, TrainingReadiness, TrainingStatus, RunningTolerance,
    PersonalRecord, EnduranceScore, HillScore, RacePrediction,
)
from garminconnect.models.workouts import Workout, Badge, TrainingPlan, ScheduledWorkout
from garminconnect.models.biometrics import LactateThreshold, CyclingFTP


def _ts_to_dt(epoch_ms: int) -> datetime:
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)


def _parse_date_field(value: Any) -> datetime | None:
    """Parse a date field that may be epoch_ms (int) or ISO string."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return _ts_to_dt(int(value))
    if isinstance(value, str):
        return _parse_garmin_timestamp(value)
    return None


def extract_daily_summary(target_date: date, data: dict[str, Any]) -> DailySummary:
    return DailySummary(
        date=target_date,
        total_steps=data.get("totalSteps"),
        step_goal=data.get("dailyStepGoal"),
        total_calories=data.get("totalKilocalories"),
        active_calories=data.get("activeKilocalories"),
        bmr_calories=data.get("bmrKilocalories"),
        total_distance_meters=data.get("totalDistanceMeters"),
        floors_climbed=data.get("floorsAscended"),
        floors_goal=data.get("userFloorsAscendedGoal"),
        moderate_intensity_minutes=data.get("moderateIntensityMinutes"),
        vigorous_intensity_minutes=data.get("vigorousIntensityMinutes"),
        intensity_minutes=(data.get("moderateIntensityMinutes") or 0) + (data.get("vigorousIntensityMinutes") or 0) if data.get("moderateIntensityMinutes") is not None or data.get("vigorousIntensityMinutes") is not None else None,
        resting_heart_rate=data.get("restingHeartRate"),
        min_heart_rate=data.get("minHeartRate"),
        max_heart_rate=data.get("maxHeartRate"),
        avg_stress=data.get("averageStressLevel"),
        max_stress=data.get("maxStressLevel"),
        body_battery_high=data.get("bodyBatteryHighestValue"),
        body_battery_low=data.get("bodyBatteryLowestValue"),
        avg_spo2=data.get("averageSpo2"),
        lowest_spo2=data.get("lowestSpo2"),
        avg_respiration=data.get("avgWakingRespirationValue"),
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
    # Sleep score is nested: sleepScores.overall.value
    sleep_scores = dto.get("sleepScores", {})
    overall = sleep_scores.get("overall", {}) if isinstance(sleep_scores, dict) else {}
    sleep_score = overall.get("value") if isinstance(overall, dict) else None
    return SleepSummary(
        date=target_date,
        total_sleep_seconds=dto.get("sleepTimeSeconds"),
        deep_sleep_seconds=dto.get("deepSleepSeconds"),
        light_sleep_seconds=dto.get("lightSleepSeconds"),
        rem_sleep_seconds=dto.get("remSleepSeconds"),
        awake_seconds=dto.get("awakeSleepSeconds"),
        sleep_score=sleep_score,
        sleep_start=_ts_to_dt(dto["sleepStartTimestampGMT"]) if dto.get("sleepStartTimestampGMT") else None,
        sleep_end=_ts_to_dt(dto["sleepEndTimestampGMT"]) if dto.get("sleepEndTimestampGMT") else None,
        avg_spo2=dto.get("averageSpO2Value"),
        avg_respiration=dto.get("averageRespirationValue"),
        avg_stress=dto.get("avgSleepStress"),
        avg_hrv=data.get("avgOvernightHrv"),
        body_battery_change=data.get("bodyBatteryChange"),
    )


_SLEEP_ACTIVITY_LEVELS = {0: "deep", 1: "light", 2: "awake", 3: "rem"}


def extract_sleep_stages(data: dict[str, Any]) -> list[SleepStage]:
    """Extract sleep stages from sleepLevels array."""
    levels = data.get("sleepLevels") or []
    stages = []
    for level in levels:
        if not isinstance(level, dict):
            continue
        start = _parse_garmin_timestamp(level.get("startGMT"))
        end = _parse_garmin_timestamp(level.get("endGMT"))
        if start is None or end is None:
            continue
        activity_level = level.get("activityLevel")
        stage_name = _SLEEP_ACTIVITY_LEVELS.get(activity_level, f"unknown_{activity_level}")
        duration = int((end - start).total_seconds())
        stages.append(SleepStage(
            timestamp=start,
            stage=stage_name,
            duration_seconds=duration,
        ))
    return stages


def _parse_garmin_timestamp(value: Any) -> datetime | None:
    """Parse Garmin timestamps which come as 'YYYY-MM-DD HH:MM:SS', ISO format, or epoch ms."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return _ts_to_dt(int(value))
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _safe_int(value: Any) -> int | None:
    """Safely convert a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def extract_activity(data: dict[str, Any]) -> Activity:
    start_time = _parse_garmin_timestamp(data.get("startTimeGMT"))
    if start_time is None:
        start_time = _parse_garmin_timestamp(data.get("beginTimestamp"))

    activity_id = data.get("activityId")
    if activity_id is None:
        raise ValueError("Activity data missing required 'activityId' field")

    return Activity(
        activity_id=str(activity_id),
        activity_type=data.get("activityType", {}).get("typeKey") if isinstance(data.get("activityType"), dict) else data.get("activityType"),
        sport=data.get("sportTypeId"),
        name=data.get("activityName"),
        start_time=start_time,
        duration_seconds=_safe_int(data.get("duration")),
        elapsed_seconds=_safe_int(data.get("elapsedDuration")),
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
        # Running dynamics
        avg_ground_contact_time=data.get("avgGroundContactTime"),
        avg_ground_contact_balance=data.get("avgGroundContactBalance"),
        avg_vertical_oscillation=data.get("avgVerticalOscillation"),
        avg_stride_length=data.get("avgStrideLength"),
        avg_vertical_ratio=data.get("avgVerticalRatio"),
        # Performance
        training_load=data.get("activityTrainingLoad"),
        norm_power=data.get("normPower"),
        max_power=data.get("maxPower"),
        avg_respiration_rate=data.get("avgRespirationRate"),
        # Pacing
        moving_duration_seconds=data.get("movingDuration"),
        fastest_split_1k_seconds=data.get("fastestSplit_1000"),
        fastest_split_mile_seconds=data.get("fastestSplit_1609"),
        fastest_split_5k_seconds=data.get("fastestSplit_5000"),
        # HR zones
        hr_zone_1_seconds=data.get("hrTimeInZone_1"),
        hr_zone_2_seconds=data.get("hrTimeInZone_2"),
        hr_zone_3_seconds=data.get("hrTimeInZone_3"),
        hr_zone_4_seconds=data.get("hrTimeInZone_4"),
        hr_zone_5_seconds=data.get("hrTimeInZone_5"),
        # Metadata
        location_name=data.get("locationName"),
        lap_count=data.get("lapCount"),
        steps=data.get("steps"),
        water_estimated_ml=data.get("waterEstimated"),
        body_battery_impact=data.get("differenceBodyBattery"),
        training_effect_label=data.get("trainingEffectLabel"),
        moderate_intensity_minutes=data.get("moderateIntensityMinutes"),
        vigorous_intensity_minutes=data.get("vigorousIntensityMinutes"),
        # GPS
        start_latitude=data.get("startLatitude"),
        start_longitude=data.get("startLongitude"),
        end_latitude=data.get("endLatitude"),
        end_longitude=data.get("endLongitude"),
    )


def extract_hrv_summary(target_date: date, data: dict[str, Any]) -> HRVSummary:
    # HRV response may nest data under hrvSummary (dict) or hrvSummaries (list)
    if isinstance(data, dict):
        if "hrvSummary" in data:
            data = data["hrvSummary"]
        elif "hrvSummaries" in data:
            summaries = data["hrvSummaries"]
            if isinstance(summaries, list) and summaries:
                data = summaries[0]
    baseline = data.get("baseline") or {}
    return HRVSummary(
        date=target_date,
        weekly_avg=data.get("weeklyAvg"),
        last_night_avg=data.get("lastNightAvg"),
        last_night_5min_high=data.get("lastNight5MinHigh"),
        baseline_low=baseline.get("lowUpper") or data.get("baselineLowUpper"),
        baseline_high=baseline.get("balancedUpper") or data.get("baselineBalancedUpper"),
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
        recovery_score=entry.get("recoveryTimeFactorPercent"),
        hrv_score=entry.get("hrvFactorPercent"),
    )


def extract_body_battery_events(data: Any) -> list[BodyBatteryEvent]:
    events = []
    # API may return a list directly or a dict with "bodyBatteryEvents" key
    items = data if isinstance(data, list) else data.get("bodyBatteryEvents") or [] if isinstance(data, dict) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        # Events may be nested under an "event" sub-key
        event = item.get("event", item)
        ts_raw = event.get("startTimestampGMT") or event.get("eventStartTimeGmt")
        if ts_raw is None:
            continue
        if isinstance(ts_raw, (int, float)):
            ts = _ts_to_dt(int(ts_raw))
        else:
            ts = _parse_garmin_timestamp(str(ts_raw))
            if ts is None:
                continue
        duration_ms = event.get("durationInMilliseconds")
        events.append(BodyBatteryEvent(
            timestamp=ts,
            event_type=event.get("eventType"),
            body_battery_impact=event.get("bodyBatteryImpact"),
            duration_minutes=int(duration_ms / 60000) if duration_ms else None,
            feedback_type=event.get("feedbackType"),
        ))
    return events


def extract_intensity_minutes_readings(data: dict[str, Any]) -> list[IntensityMinutesReading]:
    """Extract from intensityMinutesEntries: [epoch_ms, moderate, vigorous]."""
    readings = []
    for entry in data.get("intensityMinutesEntries") or []:
        if not isinstance(entry, (list, tuple)) or len(entry) < 3:
            continue
        ts_ms, moderate, vigorous = entry[0], entry[1], entry[2]
        if ts_ms is None:
            continue
        try:
            readings.append(IntensityMinutesReading(
                timestamp=_ts_to_dt(int(ts_ms)),
                moderate_minutes=int(moderate) if moderate is not None else None,
                vigorous_minutes=int(vigorous) if vigorous is not None else None,
            ))
        except (ValueError, TypeError):
            continue
    return readings


def extract_floors_readings(data: dict[str, Any]) -> list[FloorsReading]:
    """Extract from floorsChartEntries: [epoch_ms, ascended, descended]."""
    readings = []
    for entry in data.get("floorsChartEntries") or []:
        if not isinstance(entry, (list, tuple)) or len(entry) < 3:
            continue
        ts_ms, ascended, descended = entry[0], entry[1], entry[2]
        if ts_ms is None:
            continue
        try:
            readings.append(FloorsReading(
                timestamp=_ts_to_dt(int(ts_ms)),
                floors_ascended=int(ascended) if ascended is not None else None,
                floors_descended=int(descended) if descended is not None else None,
            ))
        except (ValueError, TypeError):
            continue
    return readings


def extract_blood_pressure_readings(data: dict[str, Any]) -> list[BloodPressureReading]:
    """Extract all blood pressure measurements from a daily response."""
    readings = []
    for m in data.get("bloodPressureMeasurements") or []:
        if not isinstance(m, dict):
            continue
        ts = _parse_garmin_timestamp(m.get("measurementTimestampGMT"))
        if ts is None:
            continue
        readings.append(BloodPressureReading(
            timestamp=ts,
            systolic=m.get("systolic"),
            diastolic=m.get("diastolic"),
            pulse=m.get("pulse"),
            notes=m.get("notes"),
        ))
    return readings


def extract_running_tolerance(target_date: date, data: dict[str, Any]) -> RunningTolerance:
    return RunningTolerance(
        date=target_date,
        heat_acclimation=data.get("heatAcclimation"),
        altitude_acclimation=data.get("altitudeAcclimation"),
        heat_acclimation_status=data.get("heatAcclimationStatus"),
        altitude_acclimation_status=data.get("altitudeAcclimationStatus"),
    )


def extract_personal_records(data: Any) -> list[PersonalRecord]:
    records = []
    items = data if isinstance(data, list) else data.get("personalRecords", []) if isinstance(data, dict) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        record_type = item.get("personalRecordType")
        if not record_type:
            continue
        pr_date = None
        pr_time_str = item.get("prStartTimeGMT")
        if pr_time_str:
            dt = _parse_garmin_timestamp(pr_time_str)
            pr_date = dt.date() if dt else None
        records.append(PersonalRecord(
            record_type=record_type,
            activity_type=item.get("activityType"),
            value=item.get("value"),
            activity_id=str(item["activityId"]) if item.get("activityId") else None,
            pr_date=pr_date,
        ))
    return records


def extract_workouts(data: Any) -> list[Workout]:
    items = data if isinstance(data, list) else data.get("workouts", []) if isinstance(data, dict) else []
    workouts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        workout_id = item.get("workoutId")
        if not workout_id:
            continue
        sport_type = item.get("sportType")
        if isinstance(sport_type, dict):
            sport_type = sport_type.get("sportTypeKey")
        workouts.append(Workout(
            workout_id=str(workout_id),
            name=item.get("workoutName"),
            description=item.get("description"),
            sport_type=sport_type,
            created_date=_parse_date_field(item.get("createdDate")),
            updated_date=_parse_date_field(item.get("updatedDate")),
            estimated_duration_seconds=item.get("estimatedDurationInSecs"),
            estimated_distance_meters=item.get("estimatedDistanceInMeters"),
            num_steps=item.get("numberOfSteps"),
            scheduled_date=None,
        ))
    return workouts


_BADGE_CATEGORIES = {
    1: "Activity",
    2: "Steps",
    3: "Distance",
    4: "Floors",
    5: "Social",
    6: "Miscellaneous",
    7: "Challenges",
}


def extract_badges(data: Any) -> list[Badge]:
    items = data if isinstance(data, list) else data.get("badges", []) if isinstance(data, dict) else []
    badges = []
    for item in items:
        if not isinstance(item, dict):
            continue
        badge_id = item.get("badgeId")
        if not badge_id:
            continue
        earned_dt = _parse_garmin_timestamp(
            item.get("badgeEarnedDate") or item.get("earnedDate")
        )
        category = (
            item.get("badgeCategoryName")
            or _BADGE_CATEGORIES.get(item.get("badgeCategoryId"))
        )
        badges.append(Badge(
            badge_id=str(badge_id),
            name=item.get("badgeName"),
            category=category,
            earned_date=earned_dt,
            earned_number=item.get("badgeEarnedNumber") or item.get("earnedNumber"),
        ))
    return badges


def extract_training_plan(data: dict[str, Any]) -> TrainingPlan:
    sport_type = data.get("sportType")
    if isinstance(sport_type, dict):
        sport_type = sport_type.get("sportTypeKey")
    start_str = data.get("startDate")
    end_str = data.get("endDate")
    return TrainingPlan(
        plan_id=str(data.get("trainingPlanId", "")),
        name=data.get("name"),
        sport_type=sport_type,
        start_date=date.fromisoformat(start_str) if start_str else None,
        end_date=date.fromisoformat(end_str) if end_str else None,
        goal=data.get("goal"),
        status=data.get("status"),
    )


# Metric key -> (model_field, transform_fn)
_TRACKPOINT_METRIC_MAP = {
    "directLatitude": ("latitude", None),
    "directLongitude": ("longitude", None),
    "directHeartRate": ("heart_rate", lambda v: int(v) if v else None),
    "directElevation": ("altitude", None),
    "directDoubleCadence": ("cadence", lambda v: int(v / 2) if v else None),
    "directRunCadence": ("cadence", lambda v: int(v) if v else None),
    "directSpeed": ("speed", None),
    "directPower": ("power", None),
    "directTimestamp": ("_timestamp", lambda v: _ts_to_dt(int(v)) if v else None),
}


def extract_trackpoints(activity_id: str, data: dict[str, Any]) -> list[ActivityTrackpoint]:
    """Extract trackpoints from activity_gps response with dynamic metric descriptors."""
    descriptors = data.get("metricDescriptors") or []
    metrics_data = data.get("activityDetailMetrics") or []
    if not descriptors or not metrics_data:
        return []

    # Build index: position -> (field_name, transform)
    field_map: dict[int, tuple[str, Any]] = {}
    for desc in descriptors:
        key = desc.get("key", "")
        idx = desc.get("metricsIndex")
        if idx is not None and key in _TRACKPOINT_METRIC_MAP:
            field_map[idx] = _TRACKPOINT_METRIC_MAP[key]

    trackpoints = []
    for item in metrics_data:
        values = item.get("metrics", [])
        if not values:
            continue
        fields: dict[str, Any] = {"activity_id": activity_id}
        for idx, (field_name, transform) in field_map.items():
            if idx < len(values):
                raw = values[idx]
                fields[field_name] = transform(raw) if transform and raw is not None else raw
        ts = fields.pop("_timestamp", None)
        if ts is None:
            continue
        fields["timestamp"] = ts
        trackpoints.append(ActivityTrackpoint(**fields))
    return trackpoints


def extract_endurance_score(target_date: date, data: dict[str, Any]) -> EnduranceScore:
    return EnduranceScore(
        date=target_date,
        overall_score=data.get("overallScore"),
        classification=data.get("classification"),
    )


def extract_hill_score(target_date: date, data: dict[str, Any]) -> HillScore:
    return HillScore(
        date=target_date,
        overall_score=data.get("overallScore"),
        strength_score=data.get("strengthScore"),
        endurance_score=data.get("enduranceScore"),
        vo2max=data.get("vo2Max"),
    )


def extract_race_predictions(target_date: date, data: Any) -> RacePrediction:
    # May be a list; take first entry
    if isinstance(data, list) and data:
        data = data[0]
    return RacePrediction(
        date=target_date,
        time_5k_seconds=_safe_int(data.get("time5K")),
        time_10k_seconds=_safe_int(data.get("time10K")),
        time_half_marathon_seconds=_safe_int(data.get("timeHalfMarathon")),
        time_marathon_seconds=_safe_int(data.get("timeMarathon")),
    )


def extract_scheduled_workouts(data: dict[str, Any]) -> list[ScheduledWorkout]:
    """Extract scheduled workouts from calendar API response."""
    items = data.get("calendarItems") or []
    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if item_id is None:
            continue
        date_str = item.get("date")
        results.append(ScheduledWorkout(
            id=str(item_id),
            workout_id=str(item["workoutId"]) if item.get("workoutId") else None,
            title=item.get("title"),
            date=date.fromisoformat(date_str) if date_str else None,
            sport_type=item.get("sportTypeKey"),
            item_type=item.get("itemType"),
        ))
    return results


_TRAINING_STATUS_MAP = {
    0: "NOT_ENOUGH_DATA", 1: "DETRAINING", 2: "RECOVERY", 3: "MAINTAINING",
    4: "PRODUCTIVE", 5: "PEAKING", 6: "OVERREACHING", 7: "PRODUCTIVE",
    8: "UNPRODUCTIVE", 9: "NO_STATUS",
}


def extract_training_status(target_date: date, data: dict[str, Any]) -> TrainingStatus:
    vo2max_data = data.get("mostRecentVO2Max") or {}
    generic = vo2max_data.get("generic") or {}
    cycling = vo2max_data.get("cycling") or {}

    # latestTrainingStatusData is nested under mostRecentTrainingStatus, keyed by device ID
    training_status_wrapper = data.get("mostRecentTrainingStatus") or {}
    latest_map = training_status_wrapper.get("latestTrainingStatusData") or {}
    # If latestTrainingStatusData is at top level (test fixture format), try that too
    if not latest_map:
        latest_map = data.get("latestTrainingStatusData") or {}
    # Pick first device's data
    latest: dict[str, Any] = {}
    if isinstance(latest_map, dict):
        for v in latest_map.values():
            if isinstance(v, dict):
                latest = v
                break

    # trainingStatus may be numeric or string
    raw_status = latest.get("trainingStatus")
    if isinstance(raw_status, int):
        training_status = _TRAINING_STATUS_MAP.get(raw_status, f"UNKNOWN_{raw_status}")
    else:
        training_status = raw_status

    # Weekly load from acute training load DTO or load balance
    weekly_load = None
    acute = latest.get("acuteTrainingLoadDTO") or {}
    weekly_load = acute.get("dailyTrainingLoadChronic")
    if weekly_load is None:
        load_balance = data.get("mostRecentTrainingLoadBalance") or {}
        load_map = load_balance.get("metricsTrainingLoadBalanceDTOMap") or {}
        for device_data in load_map.values():
            if isinstance(device_data, dict):
                weekly_load = device_data.get("weeklyTrainingLoad")
                break

    # Load focus from feedback phrase
    load_focus = latest.get("trainingStatusFeedbackPhrase") or latest.get("loadFocus")

    return TrainingStatus(
        date=target_date,
        training_status=training_status,
        weekly_load=weekly_load,
        load_focus=load_focus,
        vo2max_running=generic.get("vo2MaxPreciseValue"),
        vo2max_cycling=(cycling or {}).get("vo2MaxPreciseValue"),
        fitness_age=generic.get("fitnessAge"),
    )


def extract_lactate_threshold(data: list[dict[str, Any]]) -> list[LactateThreshold]:
    results = []
    for item in data:
        cal_date = item.get("calendarDate")
        if not cal_date:
            continue
        results.append(LactateThreshold(
            date=date.fromisoformat(cal_date),
            sport=item.get("sport", "DEFAULT"),
            speed=item.get("speed"),
            heart_rate=item.get("hearRate"),  # Garmin typo: "hearRate" not "heartRate"
        ))
    return results


def extract_hydration(target_date: date, data: dict[str, Any]) -> Hydration:
    return Hydration(
        date=target_date,
        intake_ml=data.get("valueInML"),
        goal_ml=data.get("goalInML"),
        daily_average_ml=data.get("dailyAverageinML"),
        sweat_loss_ml=data.get("sweatLossInML"),
        activity_intake_ml=data.get("activityIntakeInML"),
    )


def extract_cycling_ftp(data: dict[str, Any]) -> CyclingFTP | None:
    cal_date = data.get("calendarDate")
    if not cal_date:
        return None
    return CyclingFTP(
        date=date.fromisoformat(cal_date),
        ftp=data.get("functionalThresholdPower"),
        source=data.get("biometricSourceType"),
    )


def extract_hrv_readings(data: dict[str, Any]) -> list[HRVReading]:
    readings_data = data.get("hrvReadings") or []
    readings = []
    for item in readings_data:
        if not isinstance(item, dict):
            continue
        ts = _parse_garmin_timestamp(item.get("readingTimeGMT"))
        value = item.get("hrvValue")
        if ts is not None and value is not None:
            readings.append(HRVReading(timestamp=ts, hrv_value=int(value)))
    return readings
