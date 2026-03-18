from urllib.parse import quote_plus

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}

    garmin_email: str = ""
    garmin_password: str = ""
    garmin_token_dir: str = "~/.garminconnect"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "garmin"
    postgres_user: str = "garmin"
    postgres_password: str = "garmin_secret"

    mongo_host: str = "localhost"
    mongo_port: int = 27017
    mongo_db: str = "garmin_raw"
    mongo_root_user: str = "garmin"
    mongo_root_password: str = ""

    poll_interval_minutes: int = 10
    backfill_days: int = 30

    mcp_transport: str = "stdio"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8080
    mcp_api_key: str = ""  # If empty, auth is disabled

    @field_validator("poll_interval_minutes")
    @classmethod
    def _poll_interval_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("poll_interval_minutes must be > 0")
        return v

    @field_validator("postgres_port", "mongo_port", "mcp_port")
    @classmethod
    def _valid_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v

    @property
    def postgres_url(self) -> str:
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        return (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def mongo_url(self) -> str:
        if self.mongo_root_user and self.mongo_root_password:
            user = quote_plus(self.mongo_root_user)
            password = quote_plus(self.mongo_root_password)
            return f"mongodb://{user}:{password}@{self.mongo_host}:{self.mongo_port}"
        return f"mongodb://{self.mongo_host}:{self.mongo_port}"


settings = Settings()
