from datetime import date
from unittest.mock import MagicMock
from garminconnect.db.repository import HealthRepository
from garminconnect.models.daily import DailySummary


def test_upsert_daily_summary():
    mock_session = MagicMock()
    repo = HealthRepository(session_factory=lambda: mock_session)
    summary = DailySummary(
        date=date(2026, 3, 17),
        total_steps=8000,
        total_calories=2100,
    )
    repo.upsert(summary)
    mock_session.merge.assert_called_once()
    mock_session.commit.assert_called_once()


def test_store_raw_response():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)
    repo = HealthRepository(session_factory=MagicMock(), mongo_db=mock_db)
    repo.store_raw(
        endpoint="daily_summary",
        date=date(2026, 3, 17),
        data={"totalSteps": 8000},
    )
    mock_collection.replace_one.assert_called_once()
