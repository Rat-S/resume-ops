from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "resume-ops-api"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    data_dir: Path = Path("/data")
    database_url: str | None = None
    strategy_model: str = "openai/gpt-4o-mini"
    work_model: str = "openai/gpt-4o-mini"
    education_model: str = "openai/gpt-4o-mini"
    skills_model: str = "openai/gpt-4o-mini"
    projects_model: str = "openai/gpt-4o-mini"
    optional_sections_model: str = "openai/gpt-4o-mini"
    default_theme: str = "jsonresume-theme-stackoverflow"
    allowed_themes: list[str] = Field(default_factory=lambda: ["jsonresume-theme-stackoverflow"])
    max_concurrent_jobs: int = 2
    callback_timeout_seconds: int = 5
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_base_url: str | None = None

    @field_validator("allowed_themes", mode="before")
    @classmethod
    def parse_allowed_themes(cls, value: object) -> list[str]:
        if value is None:
            return ["jsonresume-theme-stackoverflow"]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise ValueError("ALLOWED_THEMES must be a comma-separated string or list.")

    @field_validator("default_theme")
    @classmethod
    def validate_default_theme(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DEFAULT_THEME must not be empty.")
        return value.strip()

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite+aiosqlite:///{self.data_dir / 'resume_ops.db'}"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def schema_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / "resources" / "resume_schema.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

