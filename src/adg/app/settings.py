from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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
    secret_key: str = Field(default="change-me-to-a-long-random-secret", min_length=16)
    default_tenant_id: str = "default"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
