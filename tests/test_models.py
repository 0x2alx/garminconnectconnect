from datetime import date, datetime, timezone
from garminconnect.models.daily import DailySummary
from garminconnect.models.monitoring import HeartRateReading, StressReading
from garminconnect.models.sleep import SleepSummary
from garminconnect.models.activities import Activity
from garminconnect.models.training import HRVSummary
from garminconnect.models.sync_status import SyncStatus


def test_daily_summary_creation():
    s = DailySummary(
        date=date(2026, 3, 17),
        total_steps=8000,
        total_calories=2100,
        total_distance_meters=6400.0,
        resting_heart_rate=58,
    )
    assert s.total_steps == 8000
    assert s.date == date(2026, 3, 17)


def test_heart_rate_reading():
    hr = HeartRateReading(
        timestamp=datetime(2026, 3, 17, 10, 30, tzinfo=timezone.utc),
        heart_rate=72,
    )
    assert hr.heart_rate == 72


def test_stress_reading():
    s = StressReading(
        timestamp=datetime(2026, 3, 17, 10, 30, tzinfo=timezone.utc),
        stress_level=45,
    )
    assert s.stress_level == 45


def test_sleep_summary():
    s = SleepSummary(
        date=date(2026, 3, 17),
        total_sleep_seconds=28800,
        deep_sleep_seconds=7200,
        light_sleep_seconds=14400,
        rem_sleep_seconds=5400,
        awake_seconds=1800,
        sleep_score=82,
    )
    assert s.sleep_score == 82


def test_activity_creation():
    a = Activity(
        activity_id="12345",
        activity_type="running",
        start_time=datetime(2026, 3, 17, 7, 0, tzinfo=timezone.utc),
        duration_seconds=3600,
        distance_meters=10000.0,
    )
    assert a.activity_type == "running"


def test_hrv_summary():
    h = HRVSummary(
        date=date(2026, 3, 17),
        weekly_avg=42.5,
        last_night_avg=38.0,
        status="BALANCED",
    )
    assert h.status == "BALANCED"


def test_sync_status():
    ss = SyncStatus(
        metric_name="daily_summary",
        date=date(2026, 3, 17),
        status="completed",
    )
    assert ss.status == "completed"
