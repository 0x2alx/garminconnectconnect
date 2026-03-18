"""Task 4.1: Tests for ensure_authenticated and get_display_name."""
from unittest.mock import patch, MagicMock
import pytest
from garminconnect.auth.client import GarminAuth


class TestEnsureAuthenticated:
    def test_resume_success_no_login(self, tmp_path):
        with patch("garminconnect.auth.client.garth") as mock_garth:
            auth = GarminAuth(token_dir=str(tmp_path))
            auth.ensure_authenticated(email="a@b.com", password="pw")
            mock_garth.resume.assert_called_once()
            mock_garth.login.assert_not_called()

    def test_resume_fails_login_success(self, tmp_path):
        with patch("garminconnect.auth.client.garth") as mock_garth:
            mock_garth.resume.side_effect = Exception("no tokens")
            auth = GarminAuth(token_dir=str(tmp_path))
            auth.ensure_authenticated(email="a@b.com", password="pw")
            mock_garth.login.assert_called_once_with("a@b.com", "pw")

    def test_resume_fails_no_credentials_raises(self, tmp_path):
        with patch("garminconnect.auth.client.garth") as mock_garth:
            mock_garth.resume.side_effect = Exception("no tokens")
            auth = GarminAuth(token_dir=str(tmp_path))
            with pytest.raises(ValueError, match="No stored tokens"):
                auth.ensure_authenticated()


class TestGetDisplayName:
    def test_returns_social_display_name(self):
        with patch("garminconnect.auth.client.garth") as mock_garth:
            mock_garth.connectapi.return_value = {"displayName": "abc-uuid-123"}
            auth = GarminAuth()
            assert auth.get_display_name() == "abc-uuid-123"

    def test_falls_back_to_username_on_error(self):
        with patch("garminconnect.auth.client.garth") as mock_garth:
            mock_garth.connectapi.side_effect = Exception("API error")
            mock_garth.client.username = "fallback@email.com"
            auth = GarminAuth()
            assert auth.get_display_name() == "fallback@email.com"
