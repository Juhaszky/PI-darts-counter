"""
Configuration module for PI Darts Counter backend.
Handles environment variables and application settings.
"""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # CORS Configuration
    cors_origins: list[str] = ["*"]

    # Camera Configuration
    camera_0_id: int = 0
    camera_1_id: int = 1
    camera_2_id: int = 2
    camera_fps: int = 30
    stability_frames: int = 45  # 30fps × 1.5s
    position_tolerance_px: int = 5

    # Game Configuration
    default_mode: Literal["301", "501"] = "501"
    double_out: bool = False

    # Database Configuration
    database_url: str = "sqlite+aiosqlite:///./database/darts.db"


# Global settings instance
settings = Settings()
