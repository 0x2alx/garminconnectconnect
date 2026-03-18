# Garmin Health Data

## Description

Query health and fitness data from a Garmin Connect database. Access daily summaries, heart rate, sleep, stress, body battery, HRV, training readiness, activities, body composition, SpO2, and respiration data. Data is synced from Garmin Connect every 10 minutes and stored in TimescaleDB.

## MCP Server

- **Type:** SSE
- **URL:** `http://10.0.0.83:8080/sse`

## Available Tools

### list_tables
List all health data tables and their row counts. Use this first to understand what data is available.

### get_table_schema
Get column names and types for a specific table. Pass `table_name` as argument.

Tables: `daily_summary`, `body_composition`, `heart_rate`, `stress`, `body_battery`, `spo2`, `respiration`, `sleep_summary`, `sleep_stages`, `activities`, `activity_trackpoints`, `hrv`, `training_readiness`, `training_status`, `race_predictions`, `sync_status`

### query_health_data
Run pre-built health queries. Arguments: `query_name` (required), `start_date` (YYYY-MM-DD), `end_date` (YYYY-MM-DD), `limit` (default 30).

Available queries:
- `daily_overview` — steps, calories, resting HR, stress, body battery, SpO2
- `sleep_trend` — hours slept by stage (deep/light/REM), sleep score
- `hr_intraday` — per-minute heart rate readings
- `stress_intraday` — per-3-minute stress levels
- `activity_list` — recent activities with distance, duration, HR, calories
- `training_readiness_trend` — readiness score with sleep/recovery/HRV breakdown
- `hrv_trend` — HRV weekly average and last night average
- `body_composition_trend` — weight and body fat percentage
- `stress_intraday` — intraday stress levels

### execute_sql
Run custom read-only SQL queries against the health database. Only SELECT/WITH statements allowed. Use this for complex queries not covered by the pre-built ones.

### get_health_summary
Get a comprehensive health summary for the last N days. Pass `days` (default 7). Returns daily averages (steps, calories, RHR, stress, SpO2), sleep averages (hours, score), and activity totals.

### get_sync_status
Check when each metric was last synced and how many days have been synced successfully or failed.

## Usage Examples

**"How am I sleeping?"**
→ Use `query_health_data` with `query_name: "sleep_trend"`, `start_date: "2026-03-01"`, `end_date: "2026-03-17"`

**"What's my resting heart rate trend?"**
→ Use `query_health_data` with `query_name: "daily_overview"` and look at the `resting_heart_rate` column

**"Show me yesterday's heart rate throughout the day"**
→ Use `query_health_data` with `query_name: "hr_intraday"`, `start_date: "2026-03-16"`, `end_date: "2026-03-17"`

**"Am I ready to train today?"**
→ Use `query_health_data` with `query_name: "training_readiness_trend"` for recent days

**"What activities did I do this month?"**
→ Use `query_health_data` with `query_name: "activity_list"`, `limit: 50`

**"Compare my stress and HRV over the last 2 weeks"**
→ Use `execute_sql` with a custom query joining `daily_summary` and `hrv` tables

## Data Granularity

| Metric | Resolution | Notes |
|--------|-----------|-------|
| Heart Rate | ~1 per minute | Continuous from watch |
| Stress | ~3 minutes | 0-100 scale |
| Body Battery | ~3 minutes | 0-100 scale |
| SpO2 | Hourly averages | Mostly overnight |
| Respiration | ~2 minutes | Breaths per minute |
| Sleep | Per night | With stage breakdown |
| Daily Summary | 1 per day | Steps, calories, HR, stress, etc |
| HRV | 1 per day | Weekly avg, last night avg |
| Activities | Per activity | With GPS trackpoints |
| Body Composition | Per weigh-in | Weight, body fat, muscle mass |
