"""Tests for workout builder payload construction."""
import pytest
from garminconnect.mcp.workout_builder import build_workout_payload, pace_to_mps


def test_pace_to_mps():
    assert pace_to_mps(5, 0) == pytest.approx(3.333, abs=0.01)
    assert pace_to_mps(4, 30) == pytest.approx(3.704, abs=0.01)


def test_pace_to_mps_fast():
    assert pace_to_mps(3, 0) == pytest.approx(5.556, abs=0.01)


def test_build_simple_workout():
    payload = build_workout_payload("Test Run", sport="running", steps=[
        {"type": "warmup", "duration_seconds": 600},
        {"type": "interval", "distance_meters": 1000, "target_pace_min": [5.0, 4.5]},
        {"type": "cooldown", "duration_seconds": 300},
    ])
    assert payload["workoutName"] == "Test Run"
    assert payload["sportType"]["sportTypeKey"] == "running"
    assert len(payload["workoutSegments"][0]["workoutSteps"]) == 3


def test_build_workout_step_types():
    payload = build_workout_payload("Steps Test", steps=[
        {"type": "warmup", "duration_seconds": 300},
        {"type": "interval", "distance_meters": 400},
        {"type": "recovery", "duration_seconds": 90},
        {"type": "cooldown", "duration_seconds": 300},
    ])
    steps = payload["workoutSegments"][0]["workoutSteps"]
    assert steps[0]["stepType"]["stepTypeKey"] == "warmup"
    assert steps[1]["stepType"]["stepTypeKey"] == "interval"
    assert steps[2]["stepType"]["stepTypeKey"] == "recovery"
    assert steps[3]["stepType"]["stepTypeKey"] == "cooldown"


def test_build_workout_cycling():
    payload = build_workout_payload("Bike", sport="cycling", steps=[])
    assert payload["sportType"]["sportTypeKey"] == "cycling"


def test_build_workout_empty_steps():
    payload = build_workout_payload("Empty")
    assert payload["workoutSegments"][0]["workoutSteps"] == []


def test_build_workout_pace_target():
    payload = build_workout_payload("Pace", steps=[
        {"type": "interval", "distance_meters": 1000, "target_pace_min": [5.0, 4.0]},
    ])
    step = payload["workoutSegments"][0]["workoutSteps"][0]
    assert step["targetType"]["workoutTargetTypeKey"] == "speed.zone"
    # faster pace (4:00) = higher mps = targetValueOne
    assert step["targetValueOne"] == pytest.approx(4.167, abs=0.01)
    # slower pace (5:00) = lower mps = targetValueTwo
    assert step["targetValueTwo"] == pytest.approx(3.333, abs=0.01)


def test_build_workout_lap_button():
    """Step with no duration or distance uses lap button end condition."""
    payload = build_workout_payload("Lap", steps=[{"type": "warmup"}])
    step = payload["workoutSegments"][0]["workoutSteps"][0]
    assert step["endCondition"]["conditionTypeKey"] == "lap.button"
