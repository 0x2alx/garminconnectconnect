"""SQL query helpers for MCP tools."""
from __future__ import annotations

QUERY_TEMPLATES = {
    "daily_overview": """
        SELECT date, total_steps, total_calories, resting_heart_rate,
               avg_stress, body_battery_high, avg_spo2
        FROM daily_summary
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "sleep_trend": """
        SELECT date, total_sleep_seconds / 3600.0 AS hours_slept,
               deep_sleep_seconds / 3600.0 AS deep_hours,
               rem_sleep_seconds / 3600.0 AS rem_hours,
               sleep_score
        FROM sleep_summary
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "hr_intraday": """
        SELECT timestamp, heart_rate
        FROM heart_rate
        WHERE timestamp >= :start AND timestamp < :end
        ORDER BY timestamp
    """,
    "activity_list": """
        SELECT activity_id, activity_type, name, start_time,
               duration_seconds / 60.0 AS duration_min,
               distance_meters / 1000.0 AS distance_km,
               avg_heart_rate, calories
        FROM activities
        ORDER BY start_time DESC
        LIMIT :limit
    """,
    "training_readiness_trend": """
        SELECT date, score, level, sleep_score, recovery_score, hrv_score
        FROM training_readiness
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "hrv_trend": """
        SELECT date, weekly_avg, last_night_avg, status
        FROM hrv
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "body_composition_trend": """
        SELECT date, weight_kg, body_fat_pct, muscle_mass_kg
        FROM body_composition
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "stress_intraday": """
        SELECT timestamp, stress_level
        FROM stress
        WHERE timestamp >= :start AND timestamp < :end
        ORDER BY timestamp
    """,
}


def get_table_list() -> list[str]:
    return [
        "daily_summary", "body_composition", "heart_rate", "stress",
        "body_battery", "spo2", "respiration", "sleep_summary",
        "sleep_stages", "activities", "activity_trackpoints",
        "hrv", "training_readiness", "training_status",
        "race_predictions", "sync_status",
    ]
