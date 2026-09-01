"""
TrackCam Backend Configuration
-------------------------------
Centralized application settings loaded from environment variables (.env).

Never hard-code credentials, model paths, or thresholds anywhere else in the
codebase — always import `settings` from this module.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


class Settings(BaseSettings):
    """
    All configuration is loaded from environment variables or a `.env` file
    at the backend/ root. Defaults are safe for local development only —
    production deployments MUST override DATABASE_URL, FRONTEND_URL, etc.
    """

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---------------------------------------------------------------- App
    APP_NAME: str = "TrackCam Backend"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # ------------------------------------------------------------- CORS
    # Comma-separated list of allowed origins, e.g.
    # "http://localhost:3000,https://trackcam.example.com"
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.FRONTEND_URL.split(",") if origin.strip()]

    # --------------------------------------------------------- Database
    # Example: postgresql+psycopg2://trackcam:trackcam@localhost:5432/trackcam
    DATABASE_URL: str = "postgresql+psycopg2://trackcam:trackcam@localhost:5432/trackcam"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT_SECONDS: int = 30
    DB_ECHO: bool = False

    # ------------------------------------------------------- Model paths
    # If a path does not exist on disk, the relevant AI module must expose a
    # MODEL_NOT_AVAILABLE state instead of silently degrading accuracy.
    YOLO_MODEL_PATH: str = "models/yolo11n.pt"
    PLATE_MODEL_PATH: str = "models/plate.pt"
    REID_MODEL_PATH: str = "models/osnet_x0_25.pt"
    LSTM_MODEL_PATH: str = "models/traffic_lstm.pt"

    # ------------------------------------------------------- AI thresholds
    CONFIDENCE_THRESHOLD: float = 0.5
    STATIONARY_THRESHOLD_SECONDS: int = 300          # 5 minutes
    CONGESTION_THRESHOLD_VEHICLES: int = 350
    TRAVEL_TIME_THRESHOLD_MULTIPLIER: float = 1.5    # actual > expected * multiplier
    QUEUE_GROWTH_RATE_THRESHOLD: float = 0.4         # relative growth per interval

    # -------------------------------------------------- Video processing
    FRAME_SKIP: int = 2
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_VIDEO_EXTENSIONS: str = ".mp4,.avi,.mov,.mkv"

    @property
    def allowed_video_extensions(self) -> List[str]:
        return [ext.strip().lower() for ext in self.ALLOWED_VIDEO_EXTENSIONS.split(",") if ext.strip()]

    # ------------------------------------------------------------- Device
    FORCE_CPU: bool = False  # set True to disable CUDA even if available

    # ------------------------------------------------------------- Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    # --------------------------------------------------------- Websocket
    WS_HEARTBEAT_SECONDS: int = 30

    @field_validator("DATABASE_URL")
    @classmethod
    def _validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must not be empty")
        return v


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — Settings() is parsed only once per process."""
    return Settings()


settings = get_settings()
