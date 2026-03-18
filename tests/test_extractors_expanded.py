"""Expanded extractor tests — Groups 3.1, 3.2, 3.3 and bug-fix verifications."""
from datetime import date, datetime, timezone
import pytest

from garminconnect.sync.extractors import (
    _parse_garmin_timestamp,
    _safe_int,
    _ts_to_dt,
    extract_activity,
    extract_body_battery_readings,
    extract_body_composition,
    extract_daily_summary,
    extract_hrv_summary,
    extract_respiration_readings,
    extract_spo2_readings,
    extract_training_readiness,
)


# ── Task 3.1: Timestamp parsing ─────────────────────────────────────────

class TestTsToDt:
    def test_basic_conversion(self):
        dt = _ts_to_dt(1710662400000)  # 2024-03-17 08:00:00 UTC
        assert dt.tzinfo == timezone.utc
        assert dt.year == 2024
        assert dt.hour == 8


class TestParseGarminTimestamp:
    def test_space_separated(self):
        result = _parse_garmin_timestamp("2026-03-17 08:30:00")
        assert result == datetime(2026, 3, 17, 8, 30, 0, tzinfo=timezone.utc)

    def test_iso_t_format(self):
        result = _parse_garmin_timestamp("2026-03-17T08:30:00")
        assert result == datetime(2026, 3, 17, 8, 30, 0, tzinfo=timezone.utc)

    def test_iso_millis(self):
        result = _parse_garmin_timestamp("2026-03-17T08:30:00.123")
        assert result is not None
        assert result.second == 0
        assert result.microsecond == 123000

    def test_epoch_ms(self):
        result = _parse_garmin_timestamp(1710662400000)
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_none_input(self):
        assert _parse_garmin_timestamp(None) is None

    def test_invalid_string(self):
        assert _parse_garmin_timestamp("not-a-date") is None

    def test_iso_with_z(self):
        result = _parse_garmin_timestamp("2026-03-17T08:30:00Z")
        assert result is not None
        assert result.tzinfo is not None

    def test_float_epoch(self):
        result = _parse_garmin_timestamp(1710662400000.0)
        assert result is not None


# ── Task 3.2: Body battery, respiration, SpO2 extractors ────────────────

class TestExtractBodyBatteryReadings:
    def test_four_element_array(self):
        data = {"bodyBatteryValuesArray": [[1710662400000, "MEASURED", 75, 3]]}
        readings = extract_body_battery_readings(data)
        assert len(readings) == 1
        assert readings[0].level == 75

    def test_two_element_array(self):
        data = {"bodyBatteryValuesArray": [[1710662400000, 60]]}
        readings = extract_body_battery_readings(data)
        assert len(readings) == 1
        assert readings[0].level == 60

    def test_dict_format(self):
        data = {"bodyBatteryValuesArray": [
            {"startTimestampGMT": 1710662400000, "bodyBatteryLevel": 80}
        ]}
        readings = extract_body_battery_readings(data)
        assert len(readings) == 1
        assert readings[0].level == 80

    def test_empty_array(self):
        assert extract_body_battery_readings({"bodyBatteryValuesArray": []}) == []

    def test_none_array(self):
        assert extract_body_battery_readings({}) == []

    def test_negative_level_filtered(self):
        data = {"bodyBatteryValuesArray": [[1710662400000, "MEASURED", -1, 0]]}
        assert extract_body_battery_readings(data) == []


class TestExtractRespirationReadings:
    def test_basic_array(self):
        data = {"respirationValuesArray": [[1710662400000, 15.5], [1710666000000, 16.2]]}
        readings = extract_respiration_readings(data)
        assert len(readings) == 2
        assert readings[0].respiration_rate == 15.5

    def test_empty(self):
        assert extract_respiration_readings({"respirationValuesArray": []}) == []

    def test_none(self):
        assert extract_respiration_readings({}) == []

    def test_null_rate_skipped(self):
        data = {"respirationValuesArray": [[1710662400000, None]]}
        assert extract_respiration_readings(data) == []


class TestExtractSpO2Readings:
    def test_hourly_averages(self):
        data = {"spO2HourlyAverages": [[1710662400000, 97], [1710666000000, 96]]}
        readings = extract_spo2_readings(data)
        assert len(readings) == 2
        assert readings[0].spo2 == 97.0

    def test_continuous_readings(self):
        data = {"continuousReadingDTOList": [
            {"epochTimestamp": 1710662400000, "spo2": 98},
        ]}
        readings = extract_spo2_readings(data)
        assert len(readings) == 1
        assert readings[0].spo2 == 98.0

    def test_empty(self):
        assert extract_spo2_readings({}) == []

    def test_null_value_skipped(self):
        data = {"spO2HourlyAverages": [[1710662400000, None]]}
        assert extract_spo2_readings(data) == []


# ── Task 3.3: Activity, body composition, HRV, training readiness ───────

class TestExtractActivity:
    def test_full_dict(self):
        data = {
            "activityId": 12345,
            "activityType": {"typeKey": "running"},
            "activityName": "Morning Run",
            "startTimeGMT": "2026-03-17 07:00:00",
            "duration": 3600.0,
            "elapsedDuration": 3700.0,
            "distance": 10000.0,
            "calories": 500,
            "averageHR": 155,
            "maxHR": 180,
        }
        activity = extract_activity(data)
        assert activity.activity_id == "12345"
        assert activity.activity_type == "running"
        assert activity.duration_seconds == 3600
        assert activity.elapsed_seconds == 3700

    def test_missing_optional_fields(self):
        data = {"activityId": 99, "activityName": "Walk"}
        activity = extract_activity(data)
        assert activity.activity_id == "99"
        assert activity.duration_seconds is None
        assert activity.start_time is None

    def test_missing_activity_id_raises(self):
        with pytest.raises(ValueError, match="activityId"):
            extract_activity({"activityName": "Oops"})

    def test_non_numeric_duration(self):
        data = {"activityId": 1, "duration": "not_a_number"}
        activity = extract_activity(data)
        assert activity.duration_seconds is None

    def test_string_activity_type(self):
        data = {"activityId": 1, "activityType": "cycling"}
        activity = extract_activity(data)
        assert activity.activity_type == "cycling"


class TestExtractBodyComposition:
    def test_list_format(self):
        data = [{"date": "2026-03-17", "weight": 75.5, "bodyFat": 15.2}]
        entries = extract_body_composition(date(2026, 3, 17), data)
        assert len(entries) == 1
        assert entries[0].weight_kg == 75.5

    def test_grams_to_kg_conversion(self):
        data = [{"date": "2026-03-17", "weight": 75500}]
        entries = extract_body_composition(date(2026, 3, 17), data)
        assert entries[0].weight_kg == 75.5

    def test_dict_with_daily_weight_summaries(self):
        data = {"dailyWeightSummaries": [{"weight": 80.0}]}
        entries = extract_body_composition(date(2026, 3, 17), data)
        assert len(entries) == 1

    def test_single_dict_with_weight(self):
        data = {"weight": 70.0, "bmi": 22.5}
        entries = extract_body_composition(date(2026, 3, 17), data)
        assert len(entries) == 1
        assert entries[0].bmi == 22.5


class TestExtractHRVSummary:
    def test_nested_hrv_summaries(self):
        data = {"hrvSummaries": [{"weeklyAvg": 45.0, "lastNightAvg": 42.0, "status": "BALANCED"}]}
        hrv = extract_hrv_summary(date(2026, 3, 17), data)
        assert hrv.weekly_avg == 45.0
        assert hrv.status == "BALANCED"

    def test_flat_format(self):
        data = {"weeklyAvg": 50.0, "lastNightAvg": 48.0}
        hrv = extract_hrv_summary(date(2026, 3, 17), data)
        assert hrv.weekly_avg == 50.0


class TestExtractTrainingReadiness:
    def test_list_with_wakeup_reset(self):
        data = [
            {"inputContext": "BEFORE_SLEEP", "score": 50, "level": "LOW"},
            {"inputContext": "AFTER_WAKEUP_RESET", "score": 75, "level": "HIGH"},
        ]
        tr = extract_training_readiness(date(2026, 3, 17), data)
        assert tr.score == 75
        assert tr.level == "HIGH"

    def test_single_dict(self):
        data = {"score": 60, "level": "MODERATE", "sleepScore": 70}
        tr = extract_training_readiness(date(2026, 3, 17), data)
        assert tr.score == 60
        assert tr.sleep_score == 70

    def test_empty_list(self):
        tr = extract_training_readiness(date(2026, 3, 17), [])
        assert tr.score is None


# ── Bug fix verifications ────────────────────────────────────────────────

class TestIntensityMinutesBugFix:
    """Task 2.1: Both values 0 should yield 0, not None."""

    def test_both_zero_returns_zero(self):
        data = {"moderateIntensityMinutes": 0, "vigorousIntensityMinutes": 0}
        result = extract_daily_summary(date(2026, 3, 17), data)
        assert result.intensity_minutes == 0

    def test_both_none_returns_none(self):
        data = {}
        result = extract_daily_summary(date(2026, 3, 17), data)
        assert result.intensity_minutes is None

    def test_one_none_one_value(self):
        data = {"moderateIntensityMinutes": 10}
        result = extract_daily_summary(date(2026, 3, 17), data)
        assert result.intensity_minutes == 10


class TestSafeInt:
    def test_valid_int(self):
        assert _safe_int(42) == 42

    def test_float_string(self):
        assert _safe_int("3600.5") == 3600

    def test_none(self):
        assert _safe_int(None) is None

    def test_invalid_string(self):
        assert _safe_int("abc") is None
