from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from psycopg2.extensions import connection
from psycopg2.pool import SimpleConnectionPool


class Database:
    def __init__(self, database_url: str) -> None:
        self._pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=database_url,
        )

    def connect(self) -> None:
        db_connection = self._pool.getconn()
        self._pool.putconn(db_connection)

    def disconnect(self) -> None:
        self._pool.closeall()

    @contextmanager
    def connection(self) -> Iterator[connection]:
        db_connection = self._pool.getconn()
        db_connection.autocommit = False
        try:
            yield db_connection
            db_connection.commit()
        except Exception:
            db_connection.rollback()
            raise
        finally:
            self._pool.putconn(db_connection)

