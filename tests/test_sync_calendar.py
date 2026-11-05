from unittest.mock import MagicMock, patch

from garminconnect.sync.pipeline import SyncPipeline


def _pipeline(fetch):
    pipeline = SyncPipeline(api_client=MagicMock(), repository=MagicMock())
    pipeline._fetch_with_retry = MagicMock(side_effect=fetch)
    return pipeline


def test_calendar_month_is_sent_zero_based():
    """Garmin's calendar-service counts months from 0, so December is month=11."""
    pipeline = _pipeline(lambda *a, **k: {"calendarItems": []})
    pipeline.sync_calendar(year=2026, month=12)
    pipeline._fetch_with_retry.assert_called_once_with("calendar", year=2026, month=11)


def test_calendar_client_error_is_not_logged_as_failure():
    """A 4xx for one month means Garmin has nothing to serve, not a broken sync."""
    def fetch(*a, **k):
        raise Exception("Error in request: 404 Client Error: Not Found for url: .../month/0")

    pipeline = _pipeline(fetch)
    with patch("garminconnect.sync.pipeline.logger") as log:
        assert pipeline.sync_calendar(year=2027, month=1) == 0
    log.error.assert_not_called()
    log.warning.assert_called_once()


def test_calendar_other_errors_still_logged_as_failure():
    def fetch(*a, **k):
        raise ConnectionError("timeout")

    pipeline = _pipeline(fetch)
    with patch("garminconnect.sync.pipeline.logger") as log:
        pipeline.sync_calendar(year=2026, month=11)
    log.error.assert_called_once()
