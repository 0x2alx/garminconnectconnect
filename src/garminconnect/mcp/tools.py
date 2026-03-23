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
    "body_battery_event_timeline": """
        SELECT timestamp, event_type, body_battery_impact,
               duration_minutes, feedback_type
        FROM body_battery_events
        WHERE timestamp >= :start AND timestamp < :end
        ORDER BY timestamp
    """,
    "intensity_minutes_intraday": """
        SELECT timestamp, moderate_minutes, vigorous_minutes
        FROM intensity_minutes
        WHERE timestamp >= :start AND timestamp < :end
        ORDER BY timestamp
    """,
    "floors_intraday": """
        SELECT timestamp, floors_ascended, floors_descended
        FROM floors
        WHERE timestamp >= :start AND timestamp < :end
        ORDER BY timestamp
    """,
    "blood_pressure_trend": """
        SELECT timestamp, systolic, diastolic, pulse, notes
        FROM blood_pressure
        WHERE timestamp >= :start AND timestamp < :end
        ORDER BY timestamp DESC
    """,
    "running_tolerance_trend": """
        SELECT date, heat_acclimation, altitude_acclimation,
               heat_acclimation_status, altitude_acclimation_status
        FROM running_tolerance
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "personal_records_list": """
        SELECT record_type, activity_type, value, activity_id, pr_date
        FROM personal_records
        ORDER BY pr_date DESC
        LIMIT :limit
    """,
    "workout_list": """
        SELECT workout_id, name, sport_type, estimated_duration_seconds,
               estimated_distance_meters, num_steps, scheduled_date
        FROM workouts
        ORDER BY updated_date DESC
        LIMIT :limit
    """,
    "badges_earned": """
        SELECT badge_id, name, category, earned_date, earned_number
        FROM badges
        ORDER BY earned_date DESC
        LIMIT :limit
    """,
    "training_plan_status": """
        SELECT plan_id, name, sport_type, start_date, end_date,
               goal, status
        FROM training_plans
        ORDER BY start_date DESC
        LIMIT :limit
    """,
    "scheduled_workouts": """
        SELECT id, workout_id, title, date, sport_type, item_type
        FROM scheduled_workouts
        WHERE date >= :start AND date <= :end
        ORDER BY date
    """,
    "upcoming_workouts": """
        SELECT id, workout_id, title, date, sport_type, item_type
        FROM scheduled_workouts
        WHERE date >= CURRENT_DATE
        ORDER BY date
        LIMIT :limit
    """,
    "sleep_stages_intraday": """
        SELECT timestamp, stage, duration_seconds
        FROM sleep_stages
        WHERE timestamp >= :start AND timestamp < :end
        ORDER BY timestamp
    """,
    "activity_running_dynamics": """
        SELECT activity_id, name, start_time,
               avg_ground_contact_time, avg_ground_contact_balance,
               avg_vertical_oscillation, avg_stride_length, avg_vertical_ratio,
               training_load, norm_power
        FROM activities
        WHERE avg_ground_contact_time IS NOT NULL
        ORDER BY start_time DESC
        LIMIT :limit
    """,
    "activity_hr_zones": """
        SELECT activity_id, name, start_time, activity_type,
               hr_zone_1_seconds, hr_zone_2_seconds, hr_zone_3_seconds,
               hr_zone_4_seconds, hr_zone_5_seconds
        FROM activities
        WHERE hr_zone_1_seconds IS NOT NULL
        ORDER BY start_time DESC
        LIMIT :limit
    """,
    "endurance_hill_scores": """
        SELECT e.date, e.overall_score AS endurance, e.classification,
               h.overall_score AS hill, h.strength_score, h.endurance_score AS hill_endurance
        FROM endurance_score e
        LEFT JOIN hill_score h ON e.date = h.date
        WHERE e.date BETWEEN :start AND :end
        ORDER BY e.date DESC
    """,
    "training_status_trend": """
        SELECT date, training_status, weekly_load, load_focus,
               vo2max_running, vo2max_cycling, fitness_age
        FROM training_status
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "hrv_readings_intraday": """
        SELECT timestamp, hrv_value
        FROM hrv_readings
        WHERE timestamp >= :start AND timestamp < :end
        ORDER BY timestamp
    """,
    "activity_trackpoints": """
        SELECT timestamp, latitude, longitude, altitude,
               heart_rate, cadence, speed, power
        FROM activity_trackpoints
        WHERE activity_id = :activity_id
        ORDER BY timestamp
    """,
    "race_predictions_trend": """
        SELECT date, time_5k_seconds, time_10k_seconds,
               time_half_marathon_seconds, time_marathon_seconds
        FROM race_predictions
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "lactate_threshold_trend": """
        SELECT date, sport, speed, heart_rate
        FROM lactate_threshold
        ORDER BY date DESC
        LIMIT :limit
    """,
    "cycling_ftp_trend": """
        SELECT date, ftp, source
        FROM cycling_ftp
        ORDER BY date DESC
        LIMIT :limit
    """,
    "hydration_trend": """
        SELECT date, intake_ml, goal_ml, sweat_loss_ml, daily_average_ml
        FROM hydration
        WHERE date BETWEEN :start AND :end
        ORDER BY date DESC
    """,
    "gear_list": """
        SELECT gear_id, display_name, make, model, gear_type, status,
               date_begin, running_meters/1000.0 AS running_km,
               max_meters/1000.0 AS max_km
        FROM gear
        ORDER BY running_meters DESC
        LIMIT :limit
    """,
    "daily_hr_rollup": """
        SELECT day, min_hr, max_hr, avg_hr, readings
        FROM daily_hr_summary WHERE day BETWEEN :start AND :end ORDER BY day DESC
    """,
    "daily_stress_rollup": """
        SELECT day, avg_stress, max_stress, readings
        FROM daily_stress_summary WHERE day BETWEEN :start AND :end ORDER BY day DESC
    """,
}


def get_table_list() -> list[str]:
    return [
        "daily_summary", "body_composition", "heart_rate", "stress",
        "body_battery", "body_battery_events", "spo2", "respiration",
        "intensity_minutes", "floors", "blood_pressure",
        "sleep_summary", "sleep_stages", "activities", "activity_trackpoints",
        "hrv", "training_readiness", "training_status",
        "race_predictions", "running_tolerance", "personal_records",
        "workouts", "badges", "training_plans", "scheduled_workouts",
        "endurance_score", "hill_score", "hrv_readings", "sync_status",
        "lactate_threshold", "cycling_ftp", "hydration", "gear",
        "activity_laps",
    ]
