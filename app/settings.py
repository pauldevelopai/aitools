"""Application settings."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    DATABASE_URL: str = "postgresql://toolkitrag:changeme@db:5432/toolkitrag"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
