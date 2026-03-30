from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health_router import HealthController
from app.api.vault_router import VaultController
from app.core.config import Settings
from app.core.security import SecurityManager
from app.db.database import Database
from app.db.repository import VaultRepository
from app.db.schema_bootstrap import ensure_schema_applied
from app.services.vault_service import VaultService


class AppFactory:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._database = Database(database_url=self._settings.database_url)
        self._security_manager = SecurityManager(settings=settings)
        self._repository = VaultRepository(database=self._database)
        self._service = VaultService(repository=self._repository, security_manager=self._security_manager)

    def create_app(self) -> FastAPI:
        @asynccontextmanager
        async def lifespan(_: FastAPI):
            ensure_schema_applied(self._settings.database_url)
            self._database.connect()
            yield
            self._database.disconnect()

        prefix = self._settings.api_prefix
        app = FastAPI(
            title=self._settings.app_title,
            lifespan=lifespan,
            docs_url=f"{prefix}/docs",
            redoc_url=f"{prefix}/redoc",
            openapi_url=f"{prefix}/openapi.json",
        )

        health_controller = HealthController(database=self._database)
        vault_controller = VaultController(service=self._service)
        app.include_router(health_controller.router, prefix=prefix)
        app.include_router(vault_controller.router, prefix=prefix)
        return app


def create_app() -> FastAPI:
    settings = Settings()
    app_factory = AppFactory(settings=settings)
    return app_factory.create_app()

