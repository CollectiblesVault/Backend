from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db.database import Database


class HealthController:
    def __init__(self, database: Database) -> None:
        self._database = database
        self.router = APIRouter(tags=["health"])
        self.router.add_api_route("/health", self.healthcheck, methods=["GET"])
        self.router.add_api_route("/db-health", self.db_healthcheck, methods=["GET"])

    def healthcheck(self) -> dict[str, str]:
        return {"status": "ok"}

    def db_healthcheck(self) -> dict[str, str]:
        try:
            with self._database.connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
        except Exception as error:
            raise HTTPException(status_code=500, detail=f"DB connection failed: {error}") from error

        return {"database": "connected"}

