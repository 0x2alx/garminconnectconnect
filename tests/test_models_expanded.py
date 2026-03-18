"""Task 5.1: Tests for untested models."""
from datetime import date, datetime, timezone
from garminconnect.models.daily import BodyComposition
from garminconnect.models.monitoring import BodyBatteryReading, SpO2Reading, RespirationReading
from garminconnect.models.sleep import SleepStage
from garminconnect.models.activities import ActivityTrackpoint
from garminconnect.models.training import TrainingReadiness, TrainingStatus, RacePrediction


TS = datetime(2026, 3, 17, 10, 0, tzinfo=timezone.utc)
D = date(2026, 3, 17)


def test_body_composition():
    bc = BodyComposition(date=D, weight_kg=75.5, bmi=22.5, body_fat_pct=15.0)
    assert bc.weight_kg == 75.5
    assert bc.body_fat_pct == 15.0


def test_body_battery_reading():
    bb = BodyBatteryReading(timestamp=TS, level=80)
    assert bb.level == 80


def test_spo2_reading():
    s = SpO2Reading(timestamp=TS, spo2=97.5)
    assert s.spo2 == 97.5


def test_respiration_reading():
    r = RespirationReading(timestamp=TS, respiration_rate=16.0)
    assert r.respiration_rate == 16.0


def test_sleep_stage():
    ss = SleepStage(timestamp=TS, stage="deep", duration_seconds=300)
    assert ss.stage == "deep"
    assert ss.duration_seconds == 300


def test_activity_trackpoint():
    tp = ActivityTrackpoint(
        activity_id="12345",
        timestamp=TS,
        latitude=40.7128,
        longitude=-74.0060,
        heart_rate=155,
    )
    assert tp.latitude == 40.7128
    assert tp.heart_rate == 155


def test_training_readiness():
    tr = TrainingReadiness(date=D, score=75, level="HIGH")
    assert tr.score == 75
    assert tr.level == "HIGH"


def test_training_status():
    ts = TrainingStatus(date=D, training_status="PRODUCTIVE", weekly_load=850.0, fitness_age=25)
    assert ts.training_status == "PRODUCTIVE"
    assert ts.fitness_age == 25


def test_race_prediction():
    rp = RacePrediction(date=D, time_5k_seconds=1200, time_10k_seconds=2600)
    assert rp.time_5k_seconds == 1200
    assert rp.time_marathon_seconds is None
