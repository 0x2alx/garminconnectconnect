from unittest.mock import MagicMock
from datetime import date
from garminconnect.api.client import GarminAPIClient
from garminconnect.api.endpoints import ENDPOINTS_BY_NAME


def test_fetch_daily_summary():
    mock_auth = MagicMock()
    mock_auth.connectapi.return_value = {"totalSteps": 8000, "totalCalories": 2100}
    client = GarminAPIClient(auth=mock_auth, user_id="test_user")
    result = client.fetch("daily_summary", date=date(2026, 3, 17))
    assert result["totalSteps"] == 8000
    mock_auth.connectapi.assert_called_once()


def test_fetch_stress_no_user_id_needed():
    mock_auth = MagicMock()
    mock_auth.connectapi.return_value = {"stressData": []}
    client = GarminAPIClient(auth=mock_auth, user_id="test_user")
    result = client.fetch("stress", date=date(2026, 3, 17))
    call_url = mock_auth.connectapi.call_args[0][0]
    assert "test_user" not in call_url


def test_fetch_unknown_endpoint_raises():
    mock_auth = MagicMock()
    client = GarminAPIClient(auth=mock_auth, user_id="test_user")
    try:
        client.fetch("nonexistent_endpoint", date=date(2026, 3, 17))
        assert False, "Should have raised"
    except KeyError:
        pass


def test_all_endpoints_have_unique_names():
    names = [ep.name for ep in ENDPOINTS_BY_NAME.values()]
    assert len(names) == len(set(names))
