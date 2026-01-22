"""Application settings."""
from pydantic_settings import BaseSettings
from typing import Literal, Optional


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    DATABASE_URL: str = "postgresql://toolkitrag:changeme@db:5432/toolkitrag"

    # Embedding Provider Configuration
    EMBEDDING_PROVIDER: Literal["openai", "local_stub"] = "openai"
    OPENAI_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Admin
    ADMIN_PASSWORD: str = "admin123"

    # RAG Configuration
    RAG_TOP_K: int = 5  # Number of chunks to retrieve
    RAG_SIMILARITY_THRESHOLD: float = 0.7  # Minimum similarity score (0-1)
    RAG_MAX_CONTEXT_LENGTH: int = 4000  # Max characters for context

    # OpenAI Chat Configuration
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_CHAT_TEMPERATURE: float = 0.1  # Low temperature for factual responses

    class Config:
        env_file = ".env"
        case_sensitive = True

    def validate_embedding_config(self) -> None:
        """
        Validate embedding configuration at startup.

        Raises:
            ValueError: If OpenAI provider is selected but API key is missing
        """
        if self.EMBEDDING_PROVIDER == "openai":
            if not self.OPENAI_API_KEY or self.OPENAI_API_KEY.startswith("sk-your"):
                raise ValueError(
                    "EMBEDDING_PROVIDER is set to 'openai' but OPENAI_API_KEY is not configured. "
                    "Either set a valid OPENAI_API_KEY or change EMBEDDING_PROVIDER to 'local_stub' for testing."
                )


settings = Settings()
