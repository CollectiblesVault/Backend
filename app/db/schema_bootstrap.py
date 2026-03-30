from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from psycopg import connect

logger = logging.getLogger(__name__)


def _resolve_schema_path() -> Path | None:
    if custom := os.getenv("SCHEMA_SQL_PATH"):
        p = Path(custom)
        return p if p.is_file() else None
    here = Path(__file__).resolve()
    # Docker: /app/db/schema.sql after COPY db ./db; repo: Backend/db/schema.sql
    for candidate in (
        here.parent.parent.parent / "db" / "schema.sql",
        here.parent / "schema.sql",
    ):
        if candidate.is_file():
            return candidate
    return None


def _split_sql_statements(sql: str) -> list[str]:
    lines: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    body = "\n".join(lines)
    statements: list[str] = []
    for chunk in re.split(r";\s*\n", body):
        part = chunk.strip()
        if not part:
            continue
        statements.append(part if part.endswith(";") else f"{part};")
    return statements


def ensure_schema_applied(database_url: str) -> None:
    if os.getenv("SKIP_SCHEMA_BOOTSTRAP", "").lower() in {"1", "true", "yes"}:
        logger.info("schema bootstrap skipped (SKIP_SCHEMA_BOOTSTRAP)")
        return
    path = _resolve_schema_path()
    if not path:
        logger.error(
            "db/schema.sql not found (set SCHEMA_SQL_PATH or ship db/schema.sql with the image)",
        )
        raise RuntimeError("schema.sql not found; cannot bootstrap database")
    sql_text = path.read_text(encoding="utf-8")
    statements = _split_sql_statements(sql_text)
    with connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
    logger.info("applied schema from %s (%d statements)", path, len(statements))
