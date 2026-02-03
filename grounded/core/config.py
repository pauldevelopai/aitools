"""
GROUNDED Core Configuration - Settings management via Pydantic.

Provides centralized configuration for GROUNDED infrastructure via
environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GroundedSettings(BaseSettings):
    """
    GROUNDED infrastructure settings.

    All settings can be configured via environment variables with the
    GROUNDED_ prefix.

    Example:
        export GROUNDED_ENV=production
        export GROUNDED_DEBUG=false
        export GROUNDED_DEFAULT_EMBEDDING_PROVIDER=openai
    """

    model_config = SettingsConfigDict(
        env_prefix="GROUNDED_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode with verbose logging",
    )

    # AI Providers
    default_embedding_provider: str = Field(
        default="local_stub",
        description="Default embedding provider key",
    )
    default_completion_provider: str = Field(
        default="local_stub",
        description="Default completion provider key",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for AI providers",
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model to use",
    )
    embedding_dimensions: int = Field(
        default=1536,
        description="Embedding vector dimensions",
    )

    # Governance
    policy_enforcement_mode: Literal["enforce", "audit", "disabled"] = Field(
        default="audit",
        description="Policy enforcement mode",
    )
    audit_log_enabled: bool = Field(
        default=True,
        description="Enable audit logging",
    )

    # Integration
    partner_api_timeout: int = Field(
        default=30,
        description="Timeout in seconds for partner API calls",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.env == "development"


@lru_cache()
def get_settings() -> GroundedSettings:
    """
    Get cached GROUNDED settings instance.

    Returns:
        GroundedSettings instance (cached)
    """
    return GroundedSettings()
