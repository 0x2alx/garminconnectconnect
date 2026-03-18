---
name: garmin-health-data
description: Query Garmin Connect health and fitness data via MCP server. Access heart rate, sleep, stress, body battery, HRV, activities, SpO2, respiration, and body composition.
homepage: https://github.com/0x2alx/garminconnectconnect
metadata: {"clawdbot":{"emoji":"⌚","requires":{"bins":["mcporter"]}}}
---

# Garmin Health Data

You have access to a Garmin Connect health database via the `garmin-health` MCP server. Data is synced from Garmin Connect every 10 minutes and stored in TimescaleDB.

## Available Tools

### get_health_summary
Get a comprehensive health summary for the last N days. Pass `--days` (default 7). Returns daily averages (steps, calories, RHR, stress, SpO2), sleep averages, and activity totals.

### query_health_data
Run pre-built health queries. Pass `--query_name`, `--start_date` (YYYY-MM-DD), `--end_date` (YYYY-MM-DD), `--limit`.

Available queries:
- `daily_overview` — steps, calories, resting HR, stress, body battery, SpO2
- `sleep_trend` — hours slept by stage (deep/light/REM), sleep score
- `hr_intraday` — per-minute heart rate readings
- `stress_intraday` — per-3-minute stress levels
- `activity_list` — recent activities with distance, duration, HR, calories
- `training_readiness_trend` — readiness score with sleep/recovery/HRV breakdown
- `hrv_trend` — HRV weekly average and last night average
- `body_composition_trend` — weight and body fat percentage

### execute_sql
Run custom read-only SQL queries against the health database. Only SELECT/WITH statements allowed.

### list_tables
List all health data tables and their row counts.

### get_table_schema
Get column names and types for a specific table. Pass `--table_name`.

### get_sync_status
Check when each metric was last synced.

## Usage Examples

**General health check:**
Use `get_health_summary` with `--days 7`

**Sleep analysis:**
Use `query_health_data` with `--query_name sleep_trend --start_date 2026-03-01 --end_date 2026-03-18`

**Last activities:**
Use `query_health_data` with `--query_name activity_list --limit 10`

**Training readiness:**
Use `query_health_data` with `--query_name training_readiness_trend --start_date 2026-03-11 --end_date 2026-03-18`

**Custom query:**
Use `execute_sql` with `--query "SELECT date, total_steps, resting_heart_rate FROM daily_summary WHERE date >= CURRENT_DATE - 7 ORDER BY date DESC"`

## Data Granularity

| Metric | Resolution |
|--------|-----------|
| Heart Rate | ~1 per minute |
| Stress | ~3 minutes, 0-100 scale |
| Body Battery | ~3 minutes, 0-100 scale |
| SpO2 | Hourly averages, mostly overnight |
| Respiration | ~2 minutes, breaths/min |
| Sleep | Per night with stage breakdown |
| Daily Summary | 1 per day |
| HRV | 1 per day |
| Activities | Per activity with GPS trackpoints |
| Body Composition | Per weigh-in |
