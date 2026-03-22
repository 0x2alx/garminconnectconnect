"""Garmin-aligned date range utility.

Garmin Connect uses Monday-to-Sunday weeks and excludes today
(partial day) from all averages. This module resolves period
strings like "week", "4weeks", "month", "year", and arbitrary
day counts into (start_date, end_date) tuples matching Garmin's
conventions.
"""
from __future__ import annotations

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
        prev_monday = monday - timedelta(days=7)
        prev_sunday = monday - timedelta(days=1)
        return prev_monday, prev_sunday
    return monday, yesterday


def _resolve_4weeks(ref: date) -> tuple[date, date]:
    current_monday = _monday_of_week(ref)
    end = current_monday - timedelta(days=1)
    start = current_monday - timedelta(weeks=4)
    return start, end


def _resolve_month(ref: date, yesterday: date) -> tuple[date, date]:
    first_of_month = ref.replace(day=1)
    if ref == first_of_month:
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
