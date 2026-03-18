"""Task 4.3: Expanded pipeline tests."""
from datetime import date
from unittest.mock import MagicMock, call
from garminconnect.sync.pipeline import SyncPipeline


class TestSyncRange:
    def test_syncs_multiple_dates(self):
        mock_api = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_sync_status.return_value = None
        mock_api.fetch.return_value = {"totalSteps": 5000}
        pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
        pipeline.sync_range(date(2026, 3, 15), date(2026, 3, 17), endpoints=["daily_summary"])
        # Should call sync_date for 3 days: 15, 16, 17
        assert mock_api.fetch.call_count == 3


class TestSyncActivities:
    def test_basic(self):
        mock_api = MagicMock()
        mock_repo = MagicMock()
        mock_api.fetch.return_value = [
            {"activityId": 111, "activityName": "Run", "startTimeGMT": "2026-03-17 07:00:00"},
            {"activityId": 222, "activityName": "Walk"},
        ]
        pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
        ids = pipeline.sync_activities()
        assert ids == ["111", "222"]
        assert mock_repo.upsert.call_count == 2

    def test_empty_response(self):
        mock_api = MagicMock()
        mock_repo = MagicMock()
        mock_api.fetch.return_value = []
        pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
        assert pipeline.sync_activities() == []

    def test_dict_response(self):
        mock_api = MagicMock()
        mock_repo = MagicMock()
        mock_api.fetch.return_value = {
            "activities": [{"activityId": 333, "activityName": "Swim"}]
        }
        pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
        ids = pipeline.sync_activities()
        assert ids == ["333"]

    def test_missing_activity_id_skipped(self):
        mock_api = MagicMock()
        mock_repo = MagicMock()
        mock_api.fetch.return_value = [{"activityName": "No ID"}]
        pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
        assert pipeline.sync_activities() == []


class TestSyncBodyComposition:
    def test_basic(self):
        mock_api = MagicMock()
        mock_repo = MagicMock()
        mock_api.fetch.return_value = [{"date": "2026-03-17", "weight": 75.0}]
        pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
        count = pipeline.sync_body_composition(date(2026, 3, 10), date(2026, 3, 17))
        assert count == 1
        mock_repo.upsert_many.assert_called_once()


class TestForceFlag:
    def test_force_skips_status_check(self):
        mock_api = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_sync_status.return_value = "completed"
        mock_api.fetch.return_value = {"totalSteps": 8000}
        pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
        result = pipeline.sync_date(date(2026, 3, 17), endpoints=["daily_summary"], force=True)
        assert result["daily_summary"] == "completed"
        mock_api.fetch.assert_called_once()


class TestBodyBatteryFromStress:
    def test_extracts_body_battery_from_stress(self):
        mock_api = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_sync_status.return_value = None
        mock_api.fetch.return_value = {
            "stressValuesArray": [[1710662400000, 25]],
            "bodyBatteryValuesArray": [[1710662400000, "MEASURED", 80, 5]],
        }
        pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
        pipeline.sync_date(date(2026, 3, 17), endpoints=["stress"])
        # upsert_many called twice: once for body battery, once for stress readings
        assert mock_repo.upsert_many.call_count == 2


class TestActivityDateFix:
    """Task 2.4: store_raw should use activity's actual date, not today."""

    def test_uses_activity_start_time(self):
        mock_api = MagicMock()
        mock_repo = MagicMock()
        mock_api.fetch.return_value = [
            {"activityId": 1, "startTimeGMT": "2026-03-15 07:00:00"},
        ]
        pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
        pipeline.sync_activities()
        store_raw_call = mock_repo.store_raw.call_args
        assert store_raw_call[0][1] == date(2026, 3, 15)


class TestActivityPagination:
    """Task 6.2: Activity pagination loops until fewer results than limit."""

    def test_paginates_across_pages(self):
        mock_api = MagicMock()
        mock_repo = MagicMock()
        # Page 1: full page (2 items with limit=2), page 2: partial page (1 item)
        mock_api.fetch.side_effect = [
            [{"activityId": 1}, {"activityId": 2}],
            [{"activityId": 3}],
        ]
        pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
        ids = pipeline.sync_activities(limit=2)
        assert ids == ["1", "2", "3"]
        assert mock_api.fetch.call_count == 2

    def test_stops_at_max_activities(self):
        mock_api = MagicMock()
        mock_repo = MagicMock()
        # Returns full pages indefinitely
        mock_api.fetch.return_value = [{"activityId": i} for i in range(5)]
        pipeline = SyncPipeline(api_client=mock_api, repository=mock_repo)
        ids = pipeline.sync_activities(limit=5, max_activities=10)
        assert len(ids) <= 10
