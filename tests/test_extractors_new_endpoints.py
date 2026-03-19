import json
from datetime import date
from pathlib import Path
from garminconnect.sync.extractors import (
    extract_body_battery_events,
    extract_intensity_minutes_readings,
    extract_floors_readings,
    extract_blood_pressure_readings,
    extract_running_tolerance,
    extract_personal_records,
    extract_workouts,
    extract_badges,
    extract_training_plan,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_body_battery_events():
    data = json.loads((FIXTURES / "body_battery_events.json").read_text())
    events = extract_body_battery_events(data)
    assert len(events) == 3
    assert events[0].event_type == "CHARGED"
    assert events[0].body_battery_impact == 45
    assert events[0].feedback_type == "SLEEP"
    assert events[1].event_type == "DRAINED"
    assert events[1].body_battery_impact == -20


def test_extract_intensity_minutes():
    data = json.loads((FIXTURES / "intensity_minutes.json").read_text())
    readings = extract_intensity_minutes_readings(data)
    assert len(readings) == 3
    assert readings[0].moderate_minutes == 5
    assert readings[0].vigorous_minutes == 0
    assert readings[1].vigorous_minutes == 5


def test_extract_floors():
    data = json.loads((FIXTURES / "floors.json").read_text())
    readings = extract_floors_readings(data)
    assert len(readings) == 3
    assert readings[0].floors_ascended == 3
    assert readings[0].floors_descended == 1
    assert readings[1].floors_ascended == 5


def test_extract_blood_pressure_readings():
    data = json.loads((FIXTURES / "blood_pressure.json").read_text())
    readings = extract_blood_pressure_readings(data)
    assert len(readings) == 1
    assert readings[0].systolic == 120
    assert readings[0].diastolic == 80
    assert readings[0].pulse == 65
    assert readings[0].notes == "Morning reading"


def test_extract_blood_pressure_empty():
    readings = extract_blood_pressure_readings({"bloodPressureMeasurements": []})
    assert readings == []


def test_extract_running_tolerance():
    data = json.loads((FIXTURES / "running_tolerance.json").read_text())
    rt = extract_running_tolerance(date(2026, 3, 19), data)
    assert rt.heat_acclimation == 75.5
    assert rt.altitude_acclimation == 30.2
    assert rt.heat_acclimation_status == "ACCLIMATED"


def test_extract_personal_records():
    data = json.loads((FIXTURES / "personal_records.json").read_text())
    records = extract_personal_records(data)
    assert len(records) == 2
    assert records[0].record_type == "LONGEST_RUN"
    assert records[0].value == 42195.0
    assert records[0].activity_id == "12345678901"


def test_extract_workouts():
    data = json.loads((FIXTURES / "workouts.json").read_text())
    workouts = extract_workouts(data)
    assert len(workouts) == 2
    assert workouts[0].workout_id == "987654321"
    assert workouts[0].name == "Easy 5K Run"
    assert workouts[0].sport_type == "running"
    assert workouts[0].estimated_duration_seconds == 1800
    assert workouts[0].num_steps == 3


def test_extract_badges():
    data = json.loads((FIXTURES / "badges.json").read_text())
    badges = extract_badges(data)
    assert len(badges) == 2
    assert badges[0].badge_id == "STEPS_10000"
    assert badges[0].name == "10,000 Steps"
    assert badges[0].earned_number == 42


def test_extract_training_plan():
    data = json.loads((FIXTURES / "training_plan.json").read_text())
    plan = extract_training_plan(data)
    assert plan.plan_id == "TP_001"
    assert plan.name == "Half Marathon Training"
    assert plan.sport_type == "running"
    assert plan.status == "IN_PROGRESS"


# --- Edge case tests ---

def test_extract_body_battery_events_empty():
    assert extract_body_battery_events({}) == []
    assert extract_body_battery_events({"bodyBatteryEvents": []}) == []


def test_extract_intensity_minutes_short_entries():
    """Entries with fewer than 3 elements should be skipped."""
    data = {"intensityMinutesEntries": [[1742371200000, 5]]}
    assert extract_intensity_minutes_readings(data) == []


def test_extract_floors_empty():
    assert extract_floors_readings({}) == []


def test_extract_workouts_dict_wrapper():
    """Workouts can come wrapped in a dict with 'workouts' key."""
    data = {"workouts": [{"workoutId": 1, "workoutName": "Test", "sportType": "running"}]}
    workouts = extract_workouts(data)
    assert len(workouts) == 1
    assert workouts[0].name == "Test"


def test_extract_personal_records_missing_type():
    """Records without personalRecordType should be skipped."""
    data = [{"value": 100}]
    assert extract_personal_records(data) == []
