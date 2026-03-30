from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from psycopg import Connection, connect


class Database:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def connect(self) -> None:
        with connect(self._database_url) as db_connection:
            db_connection.execute("SELECT 1")

    def disconnect(self) -> None:
        return None

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        db_connection = connect(self._database_url)
        try:
            yield db_connection
            db_connection.commit()
        except Exception:
            db_connection.rollback()
            raise
        finally:
            db_connection.close()

