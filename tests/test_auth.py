from unittest.mock import patch, MagicMock
from garminconnect.auth.client import GarminAuth


def test_auth_login_stores_tokens(tmp_path):
    with patch("garminconnect.auth.client.garth") as mock_garth:
        auth = GarminAuth(token_dir=str(tmp_path))
        auth.login("test@email.com", "password123")
        mock_garth.login.assert_called_once_with("test@email.com", "password123")
        mock_garth.save.assert_called_once_with(str(tmp_path))


def test_auth_resume_from_tokens(tmp_path):
    with patch("garminconnect.auth.client.garth") as mock_garth:
        auth = GarminAuth(token_dir=str(tmp_path))
        auth.resume()
        mock_garth.resume.assert_called_once_with(str(tmp_path))


def test_auth_connectapi_delegates_to_garth():
    with patch("garminconnect.auth.client.garth") as mock_garth:
        mock_garth.connectapi.return_value = {"steps": 5000}
        auth = GarminAuth()
        result = auth.connectapi("/endpoint")
        mock_garth.connectapi.assert_called_once_with("/endpoint", params=None)
        assert result == {"steps": 5000}
