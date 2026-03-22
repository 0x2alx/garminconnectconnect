"""Task 4.2: Expanded repository tests."""
from datetime import date
from unittest.mock import MagicMock
from garminconnect.db.repository import HealthRepository
from garminconnect.models.daily import DailySummary


class TestUpsertMany:
    def test_upsert_many_merges_all(self):
        mock_session = MagicMock()
        repo = HealthRepository(session_factory=lambda: mock_session)
        models = [
            DailySummary(date=date(2026, 3, 17), total_steps=8000),
            DailySummary(date=date(2026, 3, 18), total_steps=9000),
        ]
        repo.upsert_many(models)
        assert mock_session.merge.call_count == 2
        mock_session.commit.assert_called_once()

    def test_upsert_many_rollback_on_error(self):
        mock_session = MagicMock()
        mock_session.merge.side_effect = [None, Exception("db error")]
        repo = HealthRepository(session_factory=lambda: mock_session)
        try:
            repo.upsert_many([
                DailySummary(date=date(2026, 3, 17)),
                DailySummary(date=date(2026, 3, 18)),
            ])
        except Exception:
            pass
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestGetSyncStatus:
    def test_found(self):
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.status = "completed"
        mock_session.get.return_value = mock_result
        repo = HealthRepository(session_factory=lambda: mock_session)
        assert repo.get_sync_status("daily_summary", date(2026, 3, 17)) == "completed"

    def test_not_found(self):
        mock_session = MagicMock()
        mock_session.get.return_value = None
        repo = HealthRepository(session_factory=lambda: mock_session)
        assert repo.get_sync_status("daily_summary", date(2026, 3, 17)) is None


class TestMarkSynced:
    def test_success(self):
        mock_session = MagicMock()
        repo = HealthRepository(session_factory=lambda: mock_session)
        repo.mark_synced("daily_summary", date(2026, 3, 17))
        mock_session.merge.assert_called_once()
        merged_obj = mock_session.merge.call_args[0][0]
        assert merged_obj.status == "completed"
        assert merged_obj.error is None

    def test_with_error(self):
        mock_session = MagicMock()
        repo = HealthRepository(session_factory=lambda: mock_session)
        repo.mark_synced("daily_summary", date(2026, 3, 17), error="API timeout")
        merged_obj = mock_session.merge.call_args[0][0]
        assert merged_obj.status == "failed"
        assert merged_obj.error == "API timeout"


class TestStoreRaw:
    def test_no_mongo_is_noop(self):
        repo = HealthRepository(session_factory=MagicMock(), mongo_db=None)
        # Should not raise
        repo.store_raw("daily_summary", date(2026, 3, 17), {"data": 1})
