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
    # Accepts a device index ("0", "1", "2") for USB/built-in cameras,
    # or an HTTP MJPEG URL (e.g. "http://192.168.1.100:8080/video") for IP cameras.
    camera_0_source: str = "0"
    camera_1_source: str = "1"
    camera_2_source: str = "2"
    camera_fps: int = 30
    stability_frames: int = 45  # 30fps × 1.5s
    position_tolerance_px: int = 5

    # Game Configuration
    default_mode: Literal["301", "501"] = "501"
    double_out: bool = False

    # Database Configuration
    database_url: str = "sqlite+aiosqlite:///./database/darts.db"

    # Board calibration — fractions of frame dimensions (0.0–1.0).
    # Used by CoordinateMapper for mobile-camera dart detection.
    board_center_x_pct: float = 0.5
    board_center_y_pct: float = 0.5
    board_radius_pct: float = 0.4

    # Mobile camera frame rate.
    # Stability threshold = max(5, int(1.5 × mobile_camera_fps)) frames.
    mobile_camera_fps: int = 10


# Global settings instance
settings = Settings()
