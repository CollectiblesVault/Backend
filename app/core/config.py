from __future__ import annotations

import os


class Settings:
    def __init__(self) -> None:
        self.app_title: str = os.getenv("APP_TITLE", "CollectiblesVault API")
        self.api_prefix: str = os.getenv("API_PREFIX", "/api").rstrip("/") or "/api"
        self.app_host: str = os.getenv("APP_HOST", "0.0.0.0")
        self.app_port: int = int(os.getenv("APP_PORT", "8000"))
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@93.77.160.130:5432/collectibles_vault",
        )
        self.jwt_secret: str = os.getenv("JWT_SECRET", "change_me_in_production")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_exp_minutes: int = int(os.getenv("JWT_EXP_MINUTES", "60"))
        self.upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
        self.public_base_url: str = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
        self.public_media_url_prefix: str = os.getenv("PUBLIC_MEDIA_URL_PREFIX", "").rstrip("/")

