import json
from datetime import date
from pathlib import Path
from garminconnect.sync.extractors import (
    extract_daily_summary, extract_heart_rate_readings,
    extract_stress_readings, extract_sleep_summary,
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
