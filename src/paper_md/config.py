"""Application configuration using Pydantic Settings."""

from enum import Enum
from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class VisionProvider(str, Enum):
    """Supported vision providers for figure descriptions."""

    OPENAI = "openai"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    NONE = "none"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Vision provider configuration
    vision_provider: VisionProvider = VisionProvider.OLLAMA

    # OpenAI configuration
    openai_api_key: str = ""

    # Ollama configuration (local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llava"

    # Google Gemini configuration
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Table processing
    enable_table_vision: bool = False  # Disabled by default due to LLaVA accuracy issues

    # File handling
    max_file_size_mb: int = 50
    temp_dir: Path = Path("/tmp/paper_md")

    # Job processing
    job_timeout_seconds: int = 300

    # Logging
    log_level: str = "INFO"

    @property
    def max_file_size_bytes(self) -> int:
        """Return max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
