from datetime import date
from unittest.mock import MagicMock

from garminconnect.sync.pipeline import SyncPipeline


def test_fetch_with_retry_retries_on_failure_then_succeeds():
    """API call fails twice then succeeds on the third attempt."""
    mock_api = MagicMock()
    mock_api.fetch.side_effect = [
        ConnectionError("timeout"),
        ConnectionError("timeout"),
        {"totalSteps": 8000},
    ]
    mock_repo = MagicMock()

    pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
    result = pipeline._fetch_with_retry("daily_summary", date=date(2026, 3, 17))

    assert result == {"totalSteps": 8000}
    assert mock_api.fetch.call_count == 3


def test_fetch_with_retry_raises_after_max_attempts():
    """API call fails all 3 attempts and the exception is reraised."""
    mock_api = MagicMock()
    mock_api.fetch.side_effect = ConnectionError("timeout")
    mock_repo = MagicMock()

    pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
    try:
        pipeline._fetch_with_retry("daily_summary", date=date(2026, 3, 17))
        assert False, "Expected ConnectionError to be raised"
    except ConnectionError:
        pass

    assert mock_api.fetch.call_count == 3


def test_sync_date_retries_api_call_transparently():
    """sync_date succeeds even when the underlying API call needs retries."""
    mock_api = MagicMock()
    mock_api.fetch.side_effect = [
        ConnectionError("timeout"),
        {"totalSteps": 8000},
    ]
    mock_repo = MagicMock()
    mock_repo.get_sync_status.return_value = None

    pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
    results = pipeline.sync_date(date(2026, 3, 17), endpoints=["daily_summary"])

    assert results["daily_summary"] == "completed"
    assert mock_api.fetch.call_count == 2
    mock_repo.mark_synced.assert_called_once()
