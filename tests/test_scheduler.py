from unittest.mock import MagicMock
from garminconnect.sync.scheduler import GarminScheduler


def test_scheduler_creates_jobs():
    mock_pipeline = MagicMock()
    scheduler = GarminScheduler(pipeline=mock_pipeline, interval_minutes=10)
    assert scheduler.interval_minutes == 10
    assert scheduler.pipeline is mock_pipeline


def test_scheduler_run_once_calls_sync():
    mock_pipeline = MagicMock()
    scheduler = GarminScheduler(pipeline=mock_pipeline, interval_minutes=10)
    scheduler.run_once()
    mock_pipeline.sync_date.assert_called()
    mock_pipeline.sync_activities.assert_called_once()
