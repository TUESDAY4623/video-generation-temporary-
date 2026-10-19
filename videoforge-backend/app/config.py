"""Configuration management using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "VideoForge"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # ---- Server ----
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # ---- Database ----
    database_url: str = Field(
        default="postgresql+psycopg2://videoforge:videoforge@localhost:5432/videoforge"
    )
    db_echo: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def _coerce_database_url(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg2://", 1)
        return value

    # ---- Redis ----
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Default Celery URLs to Redis URL if not set
        if not self.celery_broker_url:
            self.celery_broker_url = self.redis_url
        if not self.celery_result_backend:
            self.celery_result_backend = self.redis_url

    # ---- External Service URLs ----
    presenton_url: str = "http://localhost:5001"
    elevenlabs_styltts_url: str = "http://localhost:8000"
    elevenlabs_seedvc_url: str = "http://localhost:8001"
    elevenlabs_maa_url: str = "http://localhost:8002"
    audio_service_api_key: str = "12345"

    # ---- API Keys ----
    anthropic_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    google_api_key: str = Field(default="")
    elevenlabs_api_key: str = Field(default="")
    elevenlabs_voice_id: str = Field(default="")

    # ---- Storage ----
    projects_dir: Path = Field(default=Path("./projects"))
    storage_dir: Path = Field(default=Path("./storage"))
    compose_dir: Path = Field(default=Path("./compose"))
    skills_dir: Path = Field(default=Path("./skills"))

    def model_post_init(self, __context):
        """Ensure directories exist."""
        for d in [self.projects_dir, self.storage_dir, self.compose_dir, self.skills_dir]:
            d.mkdir(parents=True, exist_ok=True)

    # ---- Pipeline ----
    max_concurrent_stages: int = 2
    stage_timeout_seconds: int = 3600
    max_retries: int = 3
    checkpoint_interval_seconds: int = 30

    # ---- Rendering ----
    default_fps: int = 30
    default_resolution: str = "1920x1080"
    default_audio_bitrate: str = "192k"
    default_video_bitrate: str = "4M"

    # ---- CORS ----
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    cors_allow_credentials: bool = True

    # ---- WebSocket ----
    ws_heartbeat_interval: int = 30

    # ---- Defaults ----
    default_wpm: int = 150
    default_target_duration_minutes: int = 45
    default_audience: str = "intermediate"
    default_visual_style: str = "cinematic"
    default_pacing: str = "moderate"
    default_topic: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
