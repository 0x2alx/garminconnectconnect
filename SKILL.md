---
name: garmin-health-data
description: Query Garmin Connect health and fitness data from a TimescaleDB database. Access heart rate, sleep, stress, body battery, HRV, activities, SpO2, respiration, and body composition.
homepage: https://github.com/0x2alx/garminconnectconnect
metadata: {"clawdbot":{"emoji":"⌚","requires":{"bins":["psql"]}}}
---

# Garmin Health Data

You have access to a Garmin Connect health database on TimescaleDB at `10.0.0.83:5432`. Data is synced from Garmin Connect every 10 minutes.

## How to Query

Use `psql` to run SQL queries:

```bash
PGPASSWORD=garmin_secret psql -h 10.0.0.83 -p 5432 -U garmin -d garmin -t -A -c "YOUR SQL HERE"
```

Flags: `-t` (tuples only, no headers), `-A` (unaligned output). Add `-F ','` for CSV output. Drop `-t -A` if you want formatted table output.

## Available Tables

| Table | What it contains | Key columns |
|-------|-----------------|-------------|
| `daily_summary` | One row per day | `date`, `total_steps`, `total_calories`, `resting_heart_rate`, `avg_stress`, `body_battery_high`, `body_battery_low`, `avg_spo2`, `floors_climbed` |
| `heart_rate` | Per-minute HR | `timestamp`, `heart_rate` |
| `stress` | Per-3-min stress | `timestamp`, `stress_level` (0-100) |
| `body_battery` | Per-3-min battery | `timestamp`, `level` (0-100) |
| `spo2` | Hourly SpO2 | `timestamp`, `spo2` |
| `respiration` | Per-2-min breathing | `timestamp`, `respiration_rate` |
| `sleep_summary` | One per night | `date`, `total_sleep_seconds`, `deep_sleep_seconds`, `light_sleep_seconds`, `rem_sleep_seconds`, `sleep_score`, `avg_hrv` |
| `activities` | Per activity | `activity_id`, `activity_type`, `name`, `start_time`, `duration_seconds`, `distance_meters`, `avg_heart_rate`, `max_heart_rate`, `calories` |
| `hrv` | Daily HRV | `date`, `weekly_avg`, `last_night_avg`, `status` |
| `training_readiness` | Daily readiness | `date`, `score`, `level`, `sleep_score`, `recovery_score`, `hrv_score` |
| `body_composition` | Per weigh-in | `date`, `weight_kg`, `body_fat_pct`, `muscle_mass_kg` |
| `training_status` | Daily status | `date`, `training_status`, `weekly_load`, `vo2max_running`, `fitness_age` |

## Common Queries

### Health summary (last 7 days)
```bash
PGPASSWORD=garmin_secret psql -h 10.0.0.83 -U garmin -d garmin -c "
SELECT date, total_steps, total_calories, resting_heart_rate, avg_stress, body_battery_high, avg_spo2
FROM daily_summary WHERE date >= CURRENT_DATE - 7 ORDER BY date DESC;"
```

### Sleep trend
```bash
PGPASSWORD=garmin_secret psql -h 10.0.0.83 -U garmin -d garmin -c "
SELECT date, total_sleep_seconds/3600.0 AS hours, deep_sleep_seconds/3600.0 AS deep_hrs,
       rem_sleep_seconds/3600.0 AS rem_hrs, sleep_score
FROM sleep_summary WHERE date >= CURRENT_DATE - 14 ORDER BY date DESC;"
```

### Recent activities
```bash
PGPASSWORD=garmin_secret psql -h 10.0.0.83 -U garmin -d garmin -c "
SELECT start_time, activity_type, name, duration_seconds/60 AS mins,
       distance_meters/1000.0 AS km, avg_heart_rate, calories
FROM activities ORDER BY start_time DESC LIMIT 10;"
```

### HRV trend
```bash
PGPASSWORD=garmin_secret psql -h 10.0.0.83 -U garmin -d garmin -c "
SELECT date, weekly_avg, last_night_avg, status FROM hrv
WHERE date >= CURRENT_DATE - 30 ORDER BY date DESC;"
```

### Training readiness
```bash
PGPASSWORD=garmin_secret psql -h 10.0.0.83 -U garmin -d garmin -c "
SELECT date, score, level, sleep_score, recovery_score, hrv_score
FROM training_readiness WHERE date >= CURRENT_DATE - 7 ORDER BY date DESC;"
```

### Intraday heart rate (specific day)
```bash
PGPASSWORD=garmin_secret psql -h 10.0.0.83 -U garmin -d garmin -c "
SELECT timestamp, heart_rate FROM heart_rate
WHERE timestamp::date = '2026-03-17' ORDER BY timestamp;"
```

### Body composition trend
```bash
PGPASSWORD=garmin_secret psql -h 10.0.0.83 -U garmin -d garmin -c "
SELECT date, weight_kg, body_fat_pct, muscle_mass_kg FROM body_composition ORDER BY date DESC;"
```

## Tips

- Use `CURRENT_DATE` and `CURRENT_DATE - N` for relative date ranges
- Cast timestamps to date with `::date` for filtering by day
- Use `AVG()`, `MIN()`, `MAX()` for aggregations
- Use `ROUND(value::numeric, 1)` to format decimal output
- Intraday tables (heart_rate, stress, body_battery, respiration, spo2) can be large — always filter by date range
- The database is read-only for analysis — do not INSERT/UPDATE/DELETE
