from __future__ import annotations

import os
from typing import Any

import garth
import structlog

logger = structlog.get_logger()


class GarminAuth:
    """Garth-based authentication for Garmin Connect."""

    def __init__(self, token_dir: str = "~/.garminconnect"):
        self.token_dir = os.path.expanduser(token_dir)

    def login(self, email: str, password: str) -> None:
        garth.login(email, password)
        garth.save(self.token_dir)
        logger.info("logged_in", email=email)

    def resume(self) -> None:
        garth.resume(self.token_dir)
        logger.info("resumed_session", token_dir=self.token_dir)

    def connectapi(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return garth.connectapi(endpoint, params=params)

    def ensure_authenticated(self, email: str = "", password: str = "") -> None:
        try:
            self.resume()
        except Exception:
            if not email or not password:
                raise ValueError("No stored tokens and no credentials provided")
            self.login(email, password)
