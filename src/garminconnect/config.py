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

    poll_interval_minutes: int = 10
    backfill_days: int = 30

    mcp_transport: str = "stdio"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8080

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def mongo_url(self) -> str:
        return f"mongodb://{self.mongo_host}:{self.mongo_port}"


settings = Settings()
