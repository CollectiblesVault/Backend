from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health_router import HealthController
from app.api.vault_router import VaultController
from app.core.config import Settings
from app.core.security import SecurityManager
from app.db.database import Database
from app.db.repository import VaultRepository
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
            self._database.connect()
            yield
            self._database.disconnect()

        app = FastAPI(title=self._settings.app_title, lifespan=lifespan)

        health_controller = HealthController(database=self._database)
        vault_controller = VaultController(service=self._service)
        app.include_router(health_controller.router)
        app.include_router(vault_controller.router)
        return app


def create_app() -> FastAPI:
    settings = Settings()
    app_factory = AppFactory(settings=settings)
    return app_factory.create_app()

