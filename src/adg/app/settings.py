from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "change-me-to-a-long-random-secret"


class Settings(BaseSettings):
    """Environment-driven application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="ADG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["local", "test", "production"] = "local"
    service_name: str = "AI Data Access Gateway"
    control_plane_database_url: str = "sqlite:///./data/adg-control-plane.db"
    api_key_header: str = "X-ADG-API-Key"
    secret_key: str = Field(default=DEFAULT_SECRET_KEY, min_length=16)
    log_level: str = "INFO"

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Reject placeholder secrets when the service is configured for production use."""

        if self.env == "production" and self.secret_key == DEFAULT_SECRET_KEY:
            raise ValueError("ADG_SECRET_KEY must be set to a unique random value in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings so dependencies do not rebuild them per request."""

    return Settings()
