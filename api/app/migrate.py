"""Apply db/migrations/V*.sql in order, once each, recording them in schema_migrations.

Files use the SQL*Plus convention of a lone "/" line between statements so the
same scripts run in SQLcl or SQL*Plus without change.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import oracledb

from app import config

log = logging.getLogger(__name__)

SPLIT = re.compile(r"^\s*/\s*$", re.M)


def statements(sql: str) -> list[str]:
    out = []
    for chunk in SPLIT.split(sql):
        lines = [ln for ln in chunk.splitlines() if ln.strip() and not ln.strip().startswith("--")]
        if lines:
            out.append("\n".join(lines))
    return out


def _ensure_tracking(cur: oracledb.Cursor) -> None:
    cur.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = 'SCHEMA_MIGRATIONS'")
    if cur.fetchone()[0] == 0:
        cur.execute(
            """CREATE TABLE schema_migrations (
                 version    VARCHAR2(20) PRIMARY KEY,
                 filename   VARCHAR2(200) NOT NULL,
                 applied_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL)"""
        )


def apply_migrations(conn: oracledb.Connection, migrations_dir: Path = config.MIGRATIONS_DIR) -> list[str]:
    applied: list[str] = []
    with conn.cursor() as cur:
        _ensure_tracking(cur)
        cur.execute("SELECT version FROM schema_migrations")
        done = {r[0] for r in cur}
        for path in sorted(migrations_dir.glob("V*.sql")):
            version = path.name.split("__", 1)[0]
            if version in done:
                continue
            log.info("applying %s", path.name)
            for stmt in statements(path.read_text()):
                cur.execute(stmt)
            cur.execute(
                "INSERT INTO schema_migrations (version, filename) VALUES (:v, :f)",
                {"v": version, "f": path.name},
            )
            applied.append(path.name)
    conn.commit()
    return applied
