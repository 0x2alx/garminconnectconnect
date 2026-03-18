"""Tests for Garmin-aligned date range utility."""
from datetime import date, timedelta
import pytest
from garminconnect.utils.date_ranges import garmin_date_range


class TestWeekPeriod:
    """Garmin 'week' = Monday of current week through yesterday."""

    def test_midweek(self):
        start, end = garmin_date_range("week", reference_date=date(2026, 3, 18))
        assert start == date(2026, 3, 16)
        assert end == date(2026, 3, 17)

    def test_tuesday(self):
        start, end = garmin_date_range("week", reference_date=date(2026, 3, 17))
        assert start == date(2026, 3, 16)
        assert end == date(2026, 3, 16)

    def test_monday_falls_back_to_previous_week(self):
        start, end = garmin_date_range("week", reference_date=date(2026, 3, 16))
        assert start == date(2026, 3, 9)
        assert end == date(2026, 3, 15)

    def test_sunday(self):
        start, end = garmin_date_range("week", reference_date=date(2026, 3, 15))
        assert start == date(2026, 3, 9)
        assert end == date(2026, 3, 14)


class TestFourWeeksPeriod:
    """Garmin '4weeks' = 4 complete Mon-Sun weeks before current week."""

    def test_midweek(self):
        start, end = garmin_date_range("4weeks", reference_date=date(2026, 3, 18))
        assert start == date(2026, 2, 16)
        assert end == date(2026, 3, 15)

    def test_monday(self):
        start, end = garmin_date_range("4weeks", reference_date=date(2026, 3, 16))
        assert start == date(2026, 2, 16)
        assert end == date(2026, 3, 15)

    def test_sunday(self):
        start, end = garmin_date_range("4weeks", reference_date=date(2026, 3, 15))
        assert start == date(2026, 2, 9)
        assert end == date(2026, 3, 8)


class TestMonthPeriod:
    """Garmin 'month' = 1st of current month through yesterday."""

    def test_midmonth(self):
        start, end = garmin_date_range("month", reference_date=date(2026, 3, 18))
        assert start == date(2026, 3, 1)
        assert end == date(2026, 3, 17)

    def test_first_of_month_falls_back(self):
        start, end = garmin_date_range("month", reference_date=date(2026, 3, 1))
        assert start == date(2026, 2, 1)
        assert end == date(2026, 2, 28)

    def test_second_of_month(self):
        start, end = garmin_date_range("month", reference_date=date(2026, 3, 2))
        assert start == date(2026, 3, 1)
        assert end == date(2026, 3, 1)


class TestPreviousMonthPeriod:
    """'month-1' = full previous calendar month."""

    def test_from_march(self):
        start, end = garmin_date_range("month-1", reference_date=date(2026, 3, 18))
        assert start == date(2026, 2, 1)
        assert end == date(2026, 2, 28)

    def test_from_january(self):
        start, end = garmin_date_range("month-1", reference_date=date(2026, 1, 15))
        assert start == date(2025, 12, 1)
        assert end == date(2025, 12, 31)


class TestYearPeriod:
    """Garmin 'year' = Jan 1 through yesterday."""

    def test_midyear(self):
        start, end = garmin_date_range("year", reference_date=date(2026, 3, 18))
        assert start == date(2026, 1, 1)
        assert end == date(2026, 3, 17)

    def test_jan_1_falls_back(self):
        start, end = garmin_date_range("year", reference_date=date(2026, 1, 1))
        assert start == date(2025, 1, 1)
        assert end == date(2025, 12, 31)


class TestArbitraryDaysPeriod:
    """Numeric string = N days ending yesterday."""

    def test_seven_days(self):
        start, end = garmin_date_range("7", reference_date=date(2026, 3, 18))
        assert start == date(2026, 3, 11)
        assert end == date(2026, 3, 17)

    def test_thirty_days(self):
        start, end = garmin_date_range("30", reference_date=date(2026, 3, 18))
        assert start == date(2026, 2, 16)
        assert end == date(2026, 3, 17)

    def test_one_day(self):
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
