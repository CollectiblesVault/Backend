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
            "postgresql://postgres:postgres@db:5432/collectibles_vault",
        )
        self.jwt_secret: str = os.getenv("JWT_SECRET", "change_me_in_production")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_exp_minutes: int = int(os.getenv("JWT_EXP_MINUTES", "60"))

