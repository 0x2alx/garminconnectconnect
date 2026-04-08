"""Build Garmin Connect workout payloads from simplified step descriptions."""
from __future__ import annotations

from typing import Any


def pace_to_mps(minutes: float, seconds: float = 0) -> float:
    """Convert pace (min:sec per km) to meters per second."""
    total_seconds = minutes * 60 + seconds
    return 1000.0 / total_seconds


TARGET_TYPES = {
    "pace.zone": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"},
    "heart.rate.zone": {"workoutTargetTypeId": 4, "workoutTargetTypeKey": "heart.rate.zone"},
    "power.zone": {"workoutTargetTypeId": 2, "workoutTargetTypeKey": "power.zone"},
    "cadence": {"workoutTargetTypeId": 3, "workoutTargetTypeKey": "cadence.zone"},
}


def _build_step(step: dict[str, Any], index: int) -> dict[str, Any]:
    """Build a single workout step in Garmin's API format."""
    step_type = step.get("type", "interval")
    type_map = {
        "warmup": {"stepTypeId": 1, "stepTypeKey": "warmup"},
        "interval": {"stepTypeId": 3, "stepTypeKey": "interval"},
        "recovery": {"stepTypeId": 4, "stepTypeKey": "recovery"},
        "rest": {"stepTypeId": 5, "stepTypeKey": "rest"},
        "cooldown": {"stepTypeId": 2, "stepTypeKey": "cooldown"},
    }
    garmin_type = type_map.get(step_type, type_map["interval"])

    result: dict[str, Any] = {
        "type": "ExecutableStepDTO",
        "stepOrder": index + 1,
        "stepType": garmin_type,
    }

    # Duration condition
    if "duration_seconds" in step:
        result["endCondition"] = {
            "conditionTypeId": 2,
            "conditionTypeKey": "time",
        }
        result["endConditionValue"] = step["duration_seconds"]
    elif "distance_meters" in step:
        result["endCondition"] = {
            "conditionTypeId": 3,
            "conditionTypeKey": "distance",
        }
        result["endConditionValue"] = step["distance_meters"]
    else:
        result["endCondition"] = {
            "conditionTypeId": 1,
            "conditionTypeKey": "lap.button",
        }

    # Target: pace (min/km range)
    if "target_pace_min" in step:
        pace_range = step["target_pace_min"]
        if isinstance(pace_range, list) and len(pace_range) == 2:
            result["targetType"] = TARGET_TYPES["pace.zone"]
            result["targetValueOne"] = pace_to_mps(pace_range[1])  # faster = higher mps
            result["targetValueTwo"] = pace_to_mps(pace_range[0])  # slower = lower mps

    # Target: heart rate (bpm range)
    elif "target_hr_bpm" in step:
        hr_range = step["target_hr_bpm"]
        if isinstance(hr_range, list) and len(hr_range) == 2:
            result["targetType"] = TARGET_TYPES["heart.rate.zone"]
            result["targetValueOne"] = hr_range[0]
            result["targetValueTwo"] = hr_range[1]

    # Target: power (watts range)
    elif "target_power_watts" in step:
        power_range = step["target_power_watts"]
        if isinstance(power_range, list) and len(power_range) == 2:
            result["targetType"] = TARGET_TYPES["power.zone"]
            result["targetValueOne"] = power_range[0]
            result["targetValueTwo"] = power_range[1]

    # Target: cadence (spm range)
    elif "target_cadence_spm" in step:
        cadence_range = step["target_cadence_spm"]
        if isinstance(cadence_range, list) and len(cadence_range) == 2:
            result["targetType"] = TARGET_TYPES["cadence"]
            result["targetValueOne"] = cadence_range[0]
            result["targetValueTwo"] = cadence_range[1]

    if "description" in step:
        result["description"] = step["description"]

    return result


def build_workout_payload(
    name: str,
    sport: str = "running",
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a complete Garmin workout payload.

    Args:
        name: Workout name.
        sport: Sport type key (running, cycling, swimming, strength).
        steps: List of step dicts with keys:
            - type: warmup, interval, recovery, rest, cooldown
            - duration_seconds: Duration in seconds
            - distance_meters: Distance in meters (alternative to duration)
            - target_pace_min: [slow, fast] in min/km (e.g. [6.0, 5.0] for 6:00-5:00/km)
            - target_hr_bpm: [low, high] in bpm (e.g. [140, 160])
            - target_power_watts: [low, high] in watts (e.g. [200, 250])
            - target_cadence_spm: [low, high] in steps/min (e.g. [170, 180])
            - description: Optional step description
    """
    sport_map = {
        "running": {"sportTypeId": 1, "sportTypeKey": "running"},
        "cycling": {"sportTypeId": 2, "sportTypeKey": "cycling"},
        "swimming": {"sportTypeId": 5, "sportTypeKey": "swimming"},
        "strength": {"sportTypeId": 4, "sportTypeKey": "strength_training"},
    }
    sport_type = sport_map.get(sport, sport_map["running"])

    workout_steps = []
    for i, step in enumerate(steps or []):
        workout_steps.append(_build_step(step, i))

    return {
        "workoutName": name,
        "sportType": sport_type,
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": sport_type,
                "workoutSteps": workout_steps,
            }
        ],
    }
