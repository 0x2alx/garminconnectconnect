from datetime import date
from unittest.mock import MagicMock
from garminconnect.sync.pipeline import SyncPipeline


def test_sync_single_date():
    mock_api = MagicMock()
    mock_repo = MagicMock()
    mock_repo.get_sync_status.return_value = None
    mock_api.fetch.return_value = {"totalSteps": 8000}
    pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
    pipeline.sync_date(date(2026, 3, 17), endpoints=["daily_summary"])
    mock_api.fetch.assert_called_once()
    mock_repo.store_raw.assert_called_once()
    mock_repo.upsert_many.assert_called_once()
    mock_repo.mark_synced.assert_called_once()


def test_sync_skips_already_completed():
    mock_api = MagicMock()
    mock_repo = MagicMock()
    mock_repo.get_sync_status.return_value = "completed"
    pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
    pipeline.sync_date(date(2026, 3, 17), endpoints=["daily_summary"])
    mock_api.fetch.assert_not_called()


def test_sync_marks_failed_on_error():
    mock_api = MagicMock()
    mock_api.fetch.side_effect = Exception("API error")
    mock_repo = MagicMock()
    mock_repo.get_sync_status.return_value = None
    pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
    pipeline.sync_date(date(2026, 3, 17), endpoints=["daily_summary"])
    mock_repo.mark_synced.assert_called_once()
    assert mock_repo.mark_synced.call_args.kwargs.get("error") is not None
