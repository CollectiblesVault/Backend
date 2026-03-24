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
        required_tables = (
            "users",
            "categories",
            "collections",
            "items",
            "wishlists",
            "likes",
            "comments",
            "auction_lots",
            "bids",
            "change_events",
        )
        try:
            with self._database.connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    missing: list[str] = []
                    for table in required_tables:
                        cursor.execute(
                            """
                            SELECT EXISTS (
                                SELECT 1 FROM information_schema.tables
                                WHERE table_schema = 'public' AND table_name = %s
                            )
                            """,
                            (table,),
                        )
                        row = cursor.fetchone()
                        if not row or not row[0]:
                            missing.append(table)
                    if missing:
                        raise HTTPException(
                            status_code=503,
                            detail=(
                                "Database schema incomplete: missing table(s): "
                                + ", ".join(missing)
                                + ". Apply db/schema.sql to this database."
                            ),
                        )
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(status_code=500, detail=f"DB connection failed: {error}") from error

        return {"database": "connected"}

