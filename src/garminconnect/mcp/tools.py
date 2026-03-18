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
    "weekly_comparison": """
        WITH this_week AS (
            SELECT AVG(total_steps) AS avg_steps, AVG(total_calories) AS avg_calories,
                   AVG(resting_heart_rate) AS avg_rhr, AVG(avg_stress) AS avg_stress,
                   AVG(avg_spo2) AS avg_spo2, COUNT(*) AS days
            FROM daily_summary
            WHERE date BETWEEN :start AND :end
        ),
        last_week AS (
            SELECT AVG(total_steps) AS avg_steps, AVG(total_calories) AS avg_calories,
                   AVG(resting_heart_rate) AS avg_rhr, AVG(avg_stress) AS avg_stress,
                   AVG(avg_spo2) AS avg_spo2, COUNT(*) AS days
            FROM daily_summary
            WHERE date BETWEEN (CAST(:start AS date) - 7) AND (CAST(:end AS date) - 7)
        )
        SELECT 'this_week' AS period, * FROM this_week
        UNION ALL
        SELECT 'last_week' AS period, * FROM last_week
    """,
    "activity_detail": """
        SELECT activity_id, activity_type, start_time,
               duration_seconds, distance_meters/1000.0 AS distance_km,
               avg_heart_rate, max_heart_rate, calories,
               avg_speed, max_speed, avg_cadence,
               training_effect_aerobic, training_effect_anaerobic,
               vo2max, elevation_gain
        FROM activities
        WHERE start_time BETWEEN :start AND :end
        ORDER BY start_time DESC
        LIMIT :limit
    """,
    "personal_records": """
        SELECT activity_type,
               COUNT(*) AS total_activities,
               MAX(distance_meters)/1000.0 AS longest_km,
               MAX(calories) AS most_calories,
               MAX(avg_heart_rate) AS highest_avg_hr,
               MIN(duration_seconds) FILTER (WHERE distance_meters > 1000) AS fastest_1k_plus_seconds,
               MAX(elevation_gain) AS most_elevation
        FROM activities
        WHERE start_time BETWEEN :start AND :end
        GROUP BY activity_type
        ORDER BY total_activities DESC
        LIMIT :limit
    """,
    "recovery_analysis": """
        SELECT ds.date,
               ds.resting_heart_rate, ds.avg_stress, ds.body_battery_high, ds.body_battery_low,
               ss.total_sleep_seconds/3600.0 AS sleep_hours, ss.sleep_score,
               h.weekly_avg AS hrv_weekly, h.last_night_avg AS hrv_last_night,
               tr.score AS readiness_score, tr.sleep_score AS readiness_sleep,
               tr.recovery_score AS readiness_recovery
        FROM daily_summary ds
        LEFT JOIN sleep_summary ss ON ds.date = ss.date
        LEFT JOIN hrv h ON ds.date = h.date
        LEFT JOIN training_readiness tr ON ds.date = tr.date
        WHERE ds.date BETWEEN :start AND :end
        ORDER BY ds.date DESC
        LIMIT :limit
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
