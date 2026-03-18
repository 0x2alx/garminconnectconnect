---
name: garmin-health-data
description: Query Garmin Connect health and fitness data via MCP server. Access heart rate, sleep, stress, body battery, HRV, activities, SpO2, respiration, and body composition.
homepage: https://github.com/0x2alx/garminconnectconnect
metadata: {"clawdbot":{"emoji":"⌚","requires":{"bins":["mcporter"]}}}
---

# Garmin Health Data

You have access to a Garmin Connect health database via the `garmin-connect` MCP server. Data is synced from Garmin Connect every 10 minutes and stored in TimescaleDB.

## Connection

- **URL:** `https://10.0.0.83/mcp/sse`
- **Authentication:** Bearer token required — set `Authorization: Bearer <MCP_API_KEY>` header
- **Direct database access is not available** — all queries go through the MCP server

### mcporter config (`~/.mcporter/mcporter.json`)

```json
{
  "mcpServers": {
    "garmin-health": {
      "baseUrl": "https://10.0.0.83/mcp/sse",
      "headers": {
        "Authorization": "Bearer <MCP_API_KEY>"
      }
    }
  }
}
```

## Available Tools

### get_health_summary
Get a comprehensive health summary for a Garmin-aligned period. Pass `--period` (default "week"). Returns daily averages (steps, calories, RHR, stress, SpO2), sleep averages, and activity totals.

Period values: `week`, `4weeks`, `month`, `month-1`, `year`, or a number like `30` for arbitrary day counts. Periods use Garmin's Monday-to-Sunday week convention and exclude today (partial day).

### query_health_data
Run pre-built health queries. Pass `--query_name` and either `--period` or explicit `--start_date`/`--end_date` (YYYY-MM-DD). Optional `--limit` (default 30).

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
Use `get_health_summary` with `--period week` or `--period 4weeks`

**Sleep analysis:**
Use `query_health_data` with `--query_name sleep_trend --period month`

**Last activities:**
Use `query_health_data` with `--query_name activity_list --limit 10`

**Training readiness:**
Use `query_health_data` with `--query_name training_readiness_trend --period week`

**Explicit date range:**
Use `query_health_data` with `--query_name hr_intraday --start_date 2026-03-15 --end_date 2026-03-18`

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
