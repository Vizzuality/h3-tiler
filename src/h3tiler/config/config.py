"""App configuration"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration"""

    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    model_config = SettingsConfigDict(env_file="h3tiler/.env")


@lru_cache()
def get_settings() -> Settings:
    """Returns a Settings object with the app config"""
    return Settings()
