"""Tests for config.py — URL encoding, validation."""
import os
from unittest.mock import patch
import pytest
from garminconnect.config import Settings


def test_postgres_url_encodes_special_chars():
    s = Settings(
        postgres_user="user@org",
        postgres_password="p@ss!#word",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="garmin",
    )
    url = s.postgres_url
    # @ in user/password must be percent-encoded so they don't break the URL
    assert "user%40org" in url
    assert "p%40ss%21%23word" in url
    assert "@localhost:5432/garmin" in url


def test_postgres_url_plain_credentials():
    s = Settings(
        postgres_user="garmin",
        postgres_password="secret",
        postgres_host="db",
        postgres_port=5432,
        postgres_db="garmin",
    )
    url = s.postgres_url
    assert url == "postgresql+psycopg://garmin:secret@db:5432/garmin"


def test_mongo_url():
    s = Settings(mongo_host="mongo", mongo_port=27017)
    assert s.mongo_url == "mongodb://mongo:27017"


def test_poll_interval_must_be_positive():
    with pytest.raises(ValueError, match="poll_interval_minutes must be > 0"):
        Settings(poll_interval_minutes=0)


def test_invalid_port_rejected():
    with pytest.raises(ValueError, match="Port must be between"):
        Settings(postgres_port=0)


def test_port_too_high_rejected():
    with pytest.raises(ValueError, match="Port must be between"):
        Settings(mcp_port=70000)
