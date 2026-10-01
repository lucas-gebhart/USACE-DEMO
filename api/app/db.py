"""Thin python-oracledb layer: one pool, dict rows, explicit SQL."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import oracledb

from app import config

_pool: oracledb.ConnectionPool | None = None


def init_pool() -> oracledb.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(
            user=config.ORACLE_USER,
            password=config.ORACLE_PASSWORD,
            dsn=config.ORACLE_DSN,
            min=1,
            max=8,
            increment=1,
        )
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close(force=True)
        _pool = None


@contextmanager
def connection() -> Iterator[oracledb.Connection]:
    pool = init_pool()
    conn = pool.acquire()
    try:
        yield conn
    finally:
        pool.release(conn)


def rows_to_dicts(cursor: oracledb.Cursor) -> list[dict[str, Any]]:
    cols = [d[0].lower() for d in cursor.description]
    out = []
    for row in cursor:
        rec = {}
        for col, val in zip(cols, row, strict=True):
            if isinstance(val, oracledb.LOB):
                val = val.read()
            rec[col] = val
        out.append(rec)
    return out


def query(sql: str, **binds: Any) -> list[dict[str, Any]]:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, binds)
        return rows_to_dicts(cur)


def query_one(sql: str, **binds: Any) -> dict[str, Any] | None:
    rows = query(sql, **binds)
    return rows[0] if rows else None


def execute(sql: str, **binds: Any) -> int:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, binds)
        conn.commit()
        return cur.rowcount


def call_refcursor(call: str, **binds: Any) -> list[dict[str, Any]]:
    """Run `SELECT`-free PL/SQL that returns a SYS_REFCURSOR, e.g. legacy package functions."""
    with connection() as conn, conn.cursor() as cur:
        ref = cur.var(oracledb.DB_TYPE_CURSOR)
        cur.execute(f"BEGIN :ref := {call}; END;", {"ref": ref, **binds})
        return rows_to_dicts(ref.getvalue())
