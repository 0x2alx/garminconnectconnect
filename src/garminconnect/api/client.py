from __future__ import annotations
import time
from datetime import date
from typing import Any
import structlog
from garminconnect.api.endpoints import ENDPOINTS_BY_NAME, Endpoint
from garminconnect.auth.client import GarminAuth

logger = structlog.get_logger()
MIN_REQUEST_INTERVAL = 1.0


class GarminAPIClient:
    def __init__(self, auth: GarminAuth, user_id: str = ""):
        self.auth = auth
        self.user_id = user_id
        self._last_request_time: float = 0

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()

    def _build_url(self, endpoint: Endpoint, date: date | None = None, start: date | None = None, end: date | None = None, activity_id: str | None = None, device_id: str | None = None) -> str:
        url = endpoint.url_template
        replacements: dict[str, str] = {}
        if date:
            replacements["{date}"] = date.isoformat()
        if start:
            replacements["{start}"] = start.isoformat()
        if end:
            replacements["{end}"] = end.isoformat()
        if endpoint.requires_user_id:
            if not self.user_id:
                self.user_id = self.auth.get_display_name()
            replacements["{user_id}"] = self.user_id
        if activity_id:
            replacements["{activity_id}"] = activity_id
        if device_id:
            replacements["{device_id}"] = device_id
        for placeholder, value in replacements.items():
            url = url.replace(placeholder, value)
        return url

    def fetch(self, endpoint_name: str, params: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        endpoint = ENDPOINTS_BY_NAME[endpoint_name]
        url = self._build_url(endpoint, **kwargs)
        self._rate_limit()
        logger.debug("fetching", endpoint=endpoint_name, url=url)
        return self.auth.connectapi(url, params=params)

    def fetch_all_daily(self, target_date: date) -> dict[str, Any]:
        results: dict[str, Any] = {}
        daily_endpoints = [
            ep for ep in ENDPOINTS_BY_NAME.values()
            if ep.category.value in ("daily", "monitoring", "sleep", "training")
            and "{activity_id}" not in ep.url_template
            and "{device_id}" not in ep.url_template
            and "{start}" not in ep.url_template
        ]
        for ep in daily_endpoints:
            try:
                results[ep.name] = self.fetch(ep.name, date=target_date)
            except Exception as e:
                logger.warning("fetch_failed", endpoint=ep.name, error=str(e))
                results[ep.name] = None
        return results
