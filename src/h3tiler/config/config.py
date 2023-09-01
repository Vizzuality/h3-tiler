from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str

    model_config = SettingsConfigDict(env_file="h3tiler/.env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
