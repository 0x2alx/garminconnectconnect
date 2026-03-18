# Garmin-Aligned Date Ranges Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a date range utility that aligns "week", "4weeks", "month", "year", and arbitrary-day periods to Garmin's Monday-to-Sunday week convention (excluding today), and wire it into all MCP query paths so computed averages match the Garmin Connect app.

**Architecture:** A pure utility function `garmin_date_range(period, reference_date)` returns `(start_date, end_date)` tuples. MCP tools `get_health_summary` and `query_health_data` gain a `period` parameter that delegates to this utility. Explicit `start_date`/`end_date` still work as arbitrary range fallback.

**Tech Stack:** Python 3.12, datetime/calendar stdlib, pytest

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/garminconnect/utils/__init__.py` | Create | Empty package init |
| `src/garminconnect/utils/date_ranges.py` | Create | `garmin_date_range()` pure function |
| `tests/test_date_ranges.py` | Create | Unit tests for all period types + edge cases |
| `src/garminconnect/mcp/server.py` | Modify | Update `get_health_summary` and `query_health_data` signatures to use `period` parameter |
| `tests/test_mcp_server_expanded.py` | Modify | Add tests for new `period` parameter in MCP tools |

---

### Task 1: Create `garmin_date_range()` utility — tests first

**Files:**
- Create: `tests/test_date_ranges.py`
- Create: `src/garminconnect/utils/__init__.py`
- Create: `src/garminconnect/utils/date_ranges.py`

- [ ] **Step 1: Write failing tests for all period types**

Create `tests/test_date_ranges.py` with tests using a fixed reference date of Wednesday 2026-03-18 so results are deterministic:

```python
"""Tests for Garmin-aligned date range utility."""
from datetime import date, timedelta
import pytest
from garminconnect.utils.date_ranges import garmin_date_range


class TestWeekPeriod:
    """Garmin 'week' = Monday of current week through yesterday."""

    def test_midweek(self):
        # Wed Mar 18 -> Mon Mar 16 to Tue Mar 17
        start, end = garmin_date_range("week", reference_date=date(2026, 3, 18))
        assert start == date(2026, 3, 16)
        assert end == date(2026, 3, 17)

    def test_tuesday(self):
        # Tue Mar 17 -> Mon Mar 16 to Mon Mar 16 (just Monday)
        start, end = garmin_date_range("week", reference_date=date(2026, 3, 17))
        assert start == date(2026, 3, 16)
        assert end == date(2026, 3, 16)

    def test_monday_falls_back_to_previous_week(self):
        # Mon Mar 16 -> no current week data yet, fall back to previous full week
        # Previous week: Mon Mar 9 to Sun Mar 15
        start, end = garmin_date_range("week", reference_date=date(2026, 3, 16))
        assert start == date(2026, 3, 9)
        assert end == date(2026, 3, 15)

    def test_sunday(self):
        # Sun Mar 15 -> Mon Mar 9 to Sat Mar 14
        start, end = garmin_date_range("week", reference_date=date(2026, 3, 15))
        assert start == date(2026, 3, 9)
        assert end == date(2026, 3, 14)


class TestFourWeeksPeriod:
    """Garmin '4weeks' = 4 complete Mon-Sun weeks before current week."""

    def test_midweek(self):
        # Wed Mar 18: current week starts Mon Mar 16
        # 4 weeks back: Mon Feb 16 to Sun Mar 15
        start, end = garmin_date_range("4weeks", reference_date=date(2026, 3, 18))
        assert start == date(2026, 2, 16)
        assert end == date(2026, 3, 15)

    def test_monday(self):
        # Mon Mar 16: current week starts Mon Mar 16
        # 4 weeks back: Mon Feb 16 to Sun Mar 15
        start, end = garmin_date_range("4weeks", reference_date=date(2026, 3, 16))
        assert start == date(2026, 2, 16)
        assert end == date(2026, 3, 15)

    def test_sunday(self):
        # Sun Mar 15: current week starts Mon Mar 9
        # 4 weeks back: Mon Feb 9 to Sun Mar 8
        start, end = garmin_date_range("4weeks", reference_date=date(2026, 3, 15))
        assert start == date(2026, 2, 9)
        assert end == date(2026, 3, 8)


class TestMonthPeriod:
    """Garmin 'month' = 1st of current month through yesterday."""

    def test_midmonth(self):
        # Mar 18 -> Mar 1 to Mar 17
        start, end = garmin_date_range("month", reference_date=date(2026, 3, 18))
        assert start == date(2026, 3, 1)
        assert end == date(2026, 3, 17)

    def test_first_of_month_falls_back(self):
        # Mar 1 -> no current month data, fall back to full previous month
        # Feb 1 to Feb 28
        start, end = garmin_date_range("month", reference_date=date(2026, 3, 1))
        assert start == date(2026, 2, 1)
        assert end == date(2026, 2, 28)

    def test_second_of_month(self):
        # Mar 2 -> Mar 1 to Mar 1 (just one day)
        start, end = garmin_date_range("month", reference_date=date(2026, 3, 2))
        assert start == date(2026, 3, 1)
        assert end == date(2026, 3, 1)


class TestPreviousMonthPeriod:
    """'month-1' = full previous calendar month."""

    def test_from_march(self):
        # Any day in March -> Feb 1 to Feb 28
        start, end = garmin_date_range("month-1", reference_date=date(2026, 3, 18))
        assert start == date(2026, 2, 1)
        assert end == date(2026, 2, 28)

    def test_from_january(self):
        # Jan -> previous month = Dec of prior year
        start, end = garmin_date_range("month-1", reference_date=date(2026, 1, 15))
        assert start == date(2025, 12, 1)
        assert end == date(2025, 12, 31)


class TestYearPeriod:
    """Garmin 'year' = Jan 1 through yesterday."""

    def test_midyear(self):
        # Mar 18 -> Jan 1 to Mar 17
        start, end = garmin_date_range("year", reference_date=date(2026, 3, 18))
        assert start == date(2026, 1, 1)
        assert end == date(2026, 3, 17)

    def test_jan_1_falls_back(self):
        # Jan 1 -> fall back to full previous year
        start, end = garmin_date_range("year", reference_date=date(2026, 1, 1))
        assert start == date(2025, 1, 1)
        assert end == date(2025, 12, 31)


class TestArbitraryDaysPeriod:
    """Numeric string = N days ending yesterday."""

    def test_seven_days(self):
        # "7" from Mar 18 -> Mar 11 to Mar 17
        start, end = garmin_date_range("7", reference_date=date(2026, 3, 18))
        assert start == date(2026, 3, 11)
        assert end == date(2026, 3, 17)

    def test_thirty_days(self):
        # "30" from Mar 18 -> Feb 16 to Mar 17 (30 days ending yesterday)
        start, end = garmin_date_range("30", reference_date=date(2026, 3, 18))
        assert start == date(2026, 2, 16)
        assert end == date(2026, 3, 17)

    def test_one_day(self):
        # "1" from Mar 18 -> Mar 17 to Mar 17 (just yesterday)
        start, end = garmin_date_range("1", reference_date=date(2026, 3, 18))
        assert start == date(2026, 3, 17)
        assert end == date(2026, 3, 17)


class TestInvalidPeriod:
    def test_unknown_string_raises(self):
        with pytest.raises(ValueError, match="Unknown period"):
            garmin_date_range("invalid", reference_date=date(2026, 3, 18))

    def test_zero_days_raises(self):
        with pytest.raises(ValueError, match="must be positive"):
            garmin_date_range("0", reference_date=date(2026, 3, 18))

    def test_negative_days_raises(self):
        with pytest.raises(ValueError, match="must be positive"):
            garmin_date_range("-5", reference_date=date(2026, 3, 18))


class TestDefaultReferenceDate:
    """When no reference_date is given, uses today."""

    def test_defaults_to_today(self):
        start, end = garmin_date_range("1")
        assert end == date.today() - timedelta(days=1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_date_ranges.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'garminconnect.utils'`

- [ ] **Step 3: Create the utils package**

Create `src/garminconnect/utils/__init__.py` — empty file.

- [ ] **Step 4: Write the implementation**

Create `src/garminconnect/utils/date_ranges.py`:

```python
"""Garmin-aligned date range utility.

Garmin Connect uses Monday-to-Sunday weeks and excludes today
(partial day) from all averages. This module resolves period
strings like "week", "4weeks", "month", "year", and arbitrary
day counts into (start_date, end_date) tuples matching Garmin's
conventions.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta


def garmin_date_range(
    period: str,
    reference_date: date | None = None,
) -> tuple[date, date]:
    """Convert a period string to a Garmin-aligned (start, end) date range.

    Args:
        period: One of "week", "4weeks", "month", "month-1", "year",
                or a numeric string like "30" for arbitrary day counts.
        reference_date: The reference point (defaults to today).
                        The range always excludes this date.

    Returns:
        (start_date, end_date) tuple of date objects, both inclusive.

    Raises:
        ValueError: If period is unrecognized or invalid.
    """
    ref = reference_date or date.today()
    yesterday = ref - timedelta(days=1)

    if period == "week":
        return _resolve_week(ref, yesterday)
    elif period == "4weeks":
        return _resolve_4weeks(ref)
    elif period == "month":
        return _resolve_month(ref, yesterday)
    elif period == "month-1":
        return _resolve_previous_month(ref)
    elif period == "year":
        return _resolve_year(ref, yesterday)
    else:
        return _resolve_arbitrary_days(period, yesterday)


def _monday_of_week(d: date) -> date:
    """Return Monday of the week containing date d."""
    return d - timedelta(days=d.weekday())


def _resolve_week(ref: date, yesterday: date) -> tuple[date, date]:
    monday = _monday_of_week(ref)
    if ref == monday:
        # It's Monday — no current-week data yet, show previous full week
        prev_monday = monday - timedelta(days=7)
        prev_sunday = monday - timedelta(days=1)
        return prev_monday, prev_sunday
    return monday, yesterday


def _resolve_4weeks(ref: date) -> tuple[date, date]:
    current_monday = _monday_of_week(ref)
    end = current_monday - timedelta(days=1)  # Sunday before current week
    start = current_monday - timedelta(weeks=4)  # Monday, 4 weeks back
    return start, end


def _resolve_month(ref: date, yesterday: date) -> tuple[date, date]:
    first_of_month = ref.replace(day=1)
    if ref == first_of_month:
        # 1st of month — no current-month data, show previous month
        return _resolve_previous_month(ref)
    return first_of_month, yesterday


def _resolve_previous_month(ref: date) -> tuple[date, date]:
    first_of_current = ref.replace(day=1)
    last_of_prev = first_of_current - timedelta(days=1)
    first_of_prev = last_of_prev.replace(day=1)
    return first_of_prev, last_of_prev


def _resolve_year(ref: date, yesterday: date) -> tuple[date, date]:
    jan1 = date(ref.year, 1, 1)
    if ref == jan1:
        # Jan 1 — no current-year data, show previous year
        return date(ref.year - 1, 1, 1), date(ref.year - 1, 12, 31)
    return jan1, yesterday


def _resolve_arbitrary_days(period: str, yesterday: date) -> tuple[date, date]:
    try:
        days = int(period)
    except ValueError:
        raise ValueError(
            f"Unknown period '{period}'. "
            f"Use 'week', '4weeks', 'month', 'month-1', 'year', or a number."
        )
    if days <= 0:
        raise ValueError(f"Day count must be positive, got {days}")
    start = yesterday - timedelta(days=days - 1)
    return start, yesterday
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_date_ranges.py -v`
Expected: All 21 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/garminconnect/utils/__init__.py src/garminconnect/utils/date_ranges.py tests/test_date_ranges.py
git commit -m "feat: add Garmin-aligned date range utility

Resolves period strings (week, 4weeks, month, year, arbitrary days)
into date ranges matching Garmin Connect's Monday-to-Sunday week
convention. Always excludes today (partial day) from averages."
```

---

### Task 2: Update `get_health_summary()` to use `period` parameter

**Files:**
- Modify: `src/garminconnect/mcp/server.py:65-91`
- Modify: `tests/test_mcp_server_expanded.py`

- [ ] **Step 1: Write failing test for new period parameter**

Add to `tests/test_mcp_server_expanded.py`:

```python
class TestHealthSummaryPeriodParam:
    """get_health_summary uses garmin_date_range for period resolution."""

    def test_accepts_period_string(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        # Should not raise; DB connection error is fine
        result = _call_tool(server, "get_health_summary", {"period": "week"})
        # If we got a result (even an error from DB), the parameter was accepted
        assert result is not None

    def test_default_period_is_week(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        # Call with no args — should default to "week" not fail
        result = _call_tool(server, "get_health_summary", {})
        assert result is not None

    def test_invalid_period_returns_error(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "get_health_summary", {"period": "invalid"})
        if isinstance(result, dict) and "error" in result:
            assert "Unknown period" in result["error"]
        elif isinstance(result, list):
            # Check if error is in list format
            for r in result:
                if isinstance(r, dict) and "error" in r:
                    assert "Unknown period" in r["error"] or "Connection" in r["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mcp_server_expanded.py::TestHealthSummaryPeriodParam -v`
Expected: FAIL — `get_health_summary` doesn't accept `period` parameter yet

- [ ] **Step 3: Update `get_health_summary` implementation**

In `src/garminconnect/mcp/server.py`, replace the `get_health_summary` function (lines 65-91):

```python
    @mcp.tool()
    def get_health_summary(period: str = "week") -> dict[str, Any]:
        """Get a comprehensive health summary for a Garmin-aligned period.

        Args:
            period: "week", "4weeks", "month", "month-1", "year", or a
                    number like "30" for arbitrary day counts. Periods use
                    Garmin's Monday-to-Sunday week convention and exclude
                    today (partial day).
        """
        from garminconnect.utils.date_ranges import garmin_date_range

        try:
            start, end = garmin_date_range(period)
        except ValueError as e:
            return {"error": str(e)}

        summary: dict[str, Any] = {"period": {"start": start.isoformat(), "end": end.isoformat()}}
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT AVG(total_steps) AS avg_steps, AVG(total_calories) AS avg_calories, "
                "AVG(resting_heart_rate) AS avg_rhr, AVG(avg_stress) AS avg_stress, "
                "AVG(avg_spo2) AS avg_spo2 FROM daily_summary WHERE date BETWEEN :s AND :e"
            ), {"s": start.isoformat(), "e": end.isoformat()}).fetchone()
            if row:
                summary["daily_averages"] = dict(row._mapping)
            row = conn.execute(text(
                "SELECT AVG(total_sleep_seconds)/3600.0 AS avg_sleep_hours, "
                "AVG(sleep_score) AS avg_sleep_score FROM sleep_summary WHERE date BETWEEN :s AND :e"
            ), {"s": start.isoformat(), "e": end.isoformat()}).fetchone()
            if row:
                summary["sleep_averages"] = dict(row._mapping)
            row = conn.execute(text(
                "SELECT COUNT(*) AS count, SUM(distance_meters)/1000.0 AS total_km, "
                "SUM(calories) AS total_calories FROM activities WHERE start_time >= :s AND start_time < :e"
            ), {"s": start.isoformat(), "e": (end + timedelta(days=1)).isoformat()}).fetchone()
            if row:
                summary["activities"] = dict(row._mapping)
        return summary
```

Note: the `timedelta` import already exists at the top of `server.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mcp_server_expanded.py::TestHealthSummaryPeriodParam -v`
Expected: PASS

- [ ] **Step 5: Run all existing tests to check for regressions**

Run: `pytest tests/ --ignore=tests/test_integration.py -v`
Expected: All tests PASS (the old `test_mcp_server.py` test may need updating if it called `get_health_summary` with `days` — check and fix if needed)

- [ ] **Step 6: Commit**

```bash
git add src/garminconnect/mcp/server.py tests/test_mcp_server_expanded.py
git commit -m "feat: update get_health_summary to use Garmin-aligned period parameter

Replace days:int with period:str ('week', '4weeks', 'month', 'year',
or numeric). Includes resolved date range in response for transparency."
```

---

### Task 3: Update `query_health_data()` to support `period` parameter

**Files:**
- Modify: `src/garminconnect/mcp/server.py:38-48`
- Modify: `tests/test_mcp_server_expanded.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_mcp_server_expanded.py`:

```python
class TestQueryHealthDataPeriodParam:
    """query_health_data accepts optional period parameter."""

    def test_period_overrides_dates(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        # period should be accepted without error
        result = _call_tool(server, "query_health_data", {
            "query_name": "daily_overview",
            "period": "week",
        })
        assert result is not None

    def test_explicit_dates_still_work(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "query_health_data", {
            "query_name": "daily_overview",
            "start_date": "2026-03-01",
            "end_date": "2026-03-17",
        })
        assert result is not None

    def test_invalid_period_returns_error(self):
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "query_health_data", {
            "query_name": "daily_overview",
            "period": "invalid",
        })
        if isinstance(result, list):
            for r in result:
                if isinstance(r, dict) and "error" in r:
                    assert "Unknown period" in r["error"] or "Connection" in r["error"]

    def test_default_uses_week_when_no_dates_or_period(self):
        """When no dates or period given, defaults to 'week'."""
        server = create_mcp_server("postgresql://test:test@localhost/test")
        result = _call_tool(server, "query_health_data", {
            "query_name": "daily_overview",
        })
        assert result is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mcp_server_expanded.py::TestQueryHealthDataPeriodParam -v`
Expected: FAIL — `query_health_data` doesn't accept `period` parameter

- [ ] **Step 3: Update `query_health_data` implementation**

In `src/garminconnect/mcp/server.py`, replace the `query_health_data` function (lines 38-48):

```python
    @mcp.tool()
    def query_health_data(query_name: str, start_date: str = "", end_date: str = "", period: str = "", limit: int = 30) -> list[dict]:
        """Run a pre-built health data query.

        Available: daily_overview, sleep_trend, hr_intraday, activity_list,
        training_readiness_trend, hrv_trend, body_composition_trend, stress_intraday.

        Args:
            query_name: Name of the query template.
            start_date: Explicit start (YYYY-MM-DD). Ignored if period is set.
            end_date: Explicit end (YYYY-MM-DD). Ignored if period is set.
            period: Garmin-aligned period — "week", "4weeks", "month",
                    "month-1", "year", or a number like "30". Overrides
                    start_date/end_date.
            limit: Max rows for activity_list (default 30).
        """
        template = QUERY_TEMPLATES.get(query_name)
        if not template:
            return [{"error": f"Unknown query. Available: {list(QUERY_TEMPLATES.keys())}"}]

        if period:
            from garminconnect.utils.date_ranges import garmin_date_range
            try:
                start, end = garmin_date_range(period)
            except ValueError as e:
                return [{"error": str(e)}]
        else:
            end = date.fromisoformat(end_date) if end_date else date.today() - timedelta(days=1)
            start = date.fromisoformat(start_date) if start_date else end - timedelta(days=6)

        with engine.connect() as conn:
            result = conn.execute(text(template), {"start": start.isoformat(), "end": end.isoformat(), "limit": limit})
            return [dict(row._mapping) for row in result.fetchall()]
```

Note: the default when no period or dates are given now uses yesterday as end (excluding today) and 7 days ending yesterday as the window — consistent with the Garmin convention.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mcp_server_expanded.py::TestQueryHealthDataPeriodParam -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ --ignore=tests/test_integration.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/garminconnect/mcp/server.py tests/test_mcp_server_expanded.py
git commit -m "feat: add period parameter to query_health_data

Accepts Garmin-aligned period strings as alternative to explicit dates.
Default behavior (no args) now excludes today for consistency."
```

---

### Task 4: Verify against live database

**Files:**
- No file changes — manual verification

- [ ] **Step 1: Run the full test suite one final time**

Run: `pytest tests/ --ignore=tests/test_integration.py -v`
Expected: All tests PASS

- [ ] **Step 2: Verify 4-week averages match Garmin app**

Run a manual query against the live database to confirm the utility produces the same date range that matched Garmin earlier:

```bash
docker exec $(docker ps -q -f name=timescale) psql -U garmin -d garmin -c "
SELECT
  ROUND(AVG(total_steps)) AS avg_steps,
  ROUND(AVG(total_calories)) AS avg_calories,
  ROUND(AVG(active_calories)) AS avg_active_cal,
  MIN(date) AS from_date,
  MAX(date) AS to_date,
  COUNT(*) AS days
FROM daily_summary
WHERE date BETWEEN '2026-02-16' AND '2026-03-15';
"
```

Expected: avg_calories ≈ 3160, avg_active_cal ≈ 650 (matching Garmin app values from earlier)

- [ ] **Step 3: Test via Python to confirm utility output**

```bash
python3 -c "
from datetime import date
from garminconnect.utils.date_ranges import garmin_date_range
for p in ['week', '4weeks', 'month', 'month-1', 'year', '30']:
    s, e = garmin_date_range(p, reference_date=date(2026, 3, 18))
    print(f'{p:>8}: {s} to {e}  ({(e - s).days + 1} days)')
"
```

Expected output:
```
    week: 2026-03-16 to 2026-03-17  (2 days)
 4weeks: 2026-02-16 to 2026-03-15  (28 days)
   month: 2026-03-01 to 2026-03-17  (17 days)
 month-1: 2026-02-01 to 2026-02-28  (28 days)
    year: 2026-01-01 to 2026-03-17  (76 days)
      30: 2026-02-16 to 2026-03-17  (30 days)
```

- [ ] **Step 4: Final commit (if any fixups needed)**

```bash
git add -A
git commit -m "fix: address any issues found during live verification"
```
