import json
import pytest
from datetime import date
from pathlib import Path
from garminconnect.sync.extractors import (
    extract_daily_summary, extract_heart_rate_readings,
    extract_stress_readings, extract_sleep_summary, extract_activity,
    extract_trackpoints, extract_endurance_score, extract_hill_score,
    extract_race_predictions, extract_training_status, extract_hrv_readings,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_daily_summary():
    data = json.loads((FIXTURES / "daily_summary.json").read_text())
    result = extract_daily_summary(date(2026, 3, 17), data)
    assert result.total_steps == 8432
    assert result.resting_heart_rate == 58
    assert result.avg_spo2 == 96.5
    assert result.body_battery_high == 95


def test_extract_heart_rate_readings():
    data = json.loads((FIXTURES / "heart_rate.json").read_text())
    readings = extract_heart_rate_readings(data)
    assert len(readings) == 4
    assert readings[0].heart_rate == 62


def test_extract_stress_readings():
    data = json.loads((FIXTURES / "stress.json").read_text())
    readings = extract_stress_readings(data)
    assert len(readings) == 3
    assert readings[0].stress_level == 25


def test_extract_sleep_summary():
    data = json.loads((FIXTURES / "sleep.json").read_text())
    result = extract_sleep_summary(date(2026, 3, 17), data)
    assert result.total_sleep_seconds == 28800
    assert result.sleep_score == 82
    assert result.avg_spo2 == 95.5
    assert result.body_battery_change == 65


def test_extract_activity_running_dynamics():
    with open("tests/fixtures/activity_detail.json") as f:
        data = json.load(f)
    activity = extract_activity(data)
    assert activity.activity_id == "12345"
    assert activity.name == "Test Run"
    assert activity.avg_ground_contact_balance == pytest.approx(51.47, abs=0.01)
    assert activity.avg_ground_contact_time == pytest.approx(314.9, abs=0.1)
    assert activity.avg_vertical_oscillation == pytest.approx(6.98, abs=0.01)
    assert activity.avg_stride_length == pytest.approx(88.77, abs=0.01)
    assert activity.avg_vertical_ratio == pytest.approx(7.67, abs=0.01)
    assert activity.training_load == pytest.approx(84.69, abs=0.01)
    assert activity.norm_power == 351
    assert activity.max_power == 445
    assert activity.avg_respiration_rate == pytest.approx(33.92, abs=0.01)
    assert activity.moving_duration_seconds == pytest.approx(2359.97, abs=0.01)
    assert activity.fastest_split_1k_seconds == pytest.approx(400.78, abs=0.01)
    assert activity.fastest_split_mile_seconds == pytest.approx(651.12, abs=0.01)
    assert activity.fastest_split_5k_seconds == pytest.approx(2062.25, abs=0.01)
    assert activity.hr_zone_1_seconds == pytest.approx(69.576, abs=0.01)
    assert activity.hr_zone_3_seconds == pytest.approx(1886.351, abs=0.01)
    assert activity.hr_zone_4_seconds == 0
    assert activity.location_name == "Plantation"
    assert activity.lap_count == 7
    assert activity.steps == 6428
    assert activity.water_estimated_ml == 659
    assert activity.body_battery_impact == -8
    assert activity.training_effect_label == "AEROBIC_BASE"
    assert activity.moderate_intensity_minutes == 0
    assert activity.vigorous_intensity_minutes == 39
    assert activity.start_latitude == pytest.approx(26.1237, abs=0.001)
    assert activity.start_longitude == pytest.approx(-80.281, abs=0.001)
    assert activity.end_latitude == pytest.approx(26.1243, abs=0.001)


def test_extract_trackpoints():
    with open("tests/fixtures/activity_gps.json") as f:
        data = json.load(f)
    trackpoints = extract_trackpoints("12345", data)
    assert len(trackpoints) == 3
    tp = trackpoints[0]
    assert tp.activity_id == "12345"
    assert tp.latitude == pytest.approx(26.123, abs=0.001)
    assert tp.longitude == pytest.approx(-80.281, abs=0.001)
    assert tp.heart_rate == 155
    assert tp.altitude == pytest.approx(4.2, abs=0.1)
    assert tp.cadence == 81  # doubleCadence / 2
    assert tp.speed == pytest.approx(2.41, abs=0.01)
    assert tp.power == pytest.approx(348.0, abs=0.1)


def test_extract_endurance_score():
    with open("tests/fixtures/endurance_score.json") as f:
        data = json.load(f)
    score = extract_endurance_score(date(2026, 3, 20), data)
    assert score.overall_score == 5508
    assert score.classification == 2


def test_extract_hill_score():
    with open("tests/fixtures/hill_score.json") as f:
        data = json.load(f)
    score = extract_hill_score(date(2026, 3, 20), data)
    assert score.overall_score == 27
    assert score.strength_score == 25
    assert score.endurance_score == 13


def test_extract_race_predictions():
    with open("tests/fixtures/race_predictions.json") as f:
        data = json.load(f)
    pred = extract_race_predictions(date(2026, 3, 20), data)
    assert pred.time_5k_seconds == 1500
    assert pred.time_marathon_seconds == 14400


def test_extract_training_status():
    with open("tests/fixtures/training_status.json") as f:
        data = json.load(f)
    ts = extract_training_status(date(2026, 3, 19), data)
    assert ts.training_status == "PRODUCTIVE"
    assert ts.vo2max_running == pytest.approx(43.8, abs=0.1)
    assert ts.weekly_load == pytest.approx(450.0)
    assert ts.load_focus == "PRODUCTIVE_9"


def test_extract_hrv_readings():
    data = {
        "hrvReadings": [
            {"hrvValue": 65, "readingTimeGMT": "2026-03-17T03:57:41.0"},
            {"hrvValue": 68, "readingTimeGMT": "2026-03-17T04:02:41.0"},
        ]
    }
    readings = extract_hrv_readings(data)
    assert len(readings) == 2
    assert readings[0].hrv_value == 65
