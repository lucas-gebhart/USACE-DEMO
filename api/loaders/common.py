from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import oracledb


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def record_load(cur: oracledb.Cursor, meta: dict, row_count: int, note: str | None = None) -> int:
    """Insert a lineage row for one source fetch and return its load_id."""
    out = cur.var(oracledb.DB_TYPE_NUMBER)
    cur.execute(
        """INSERT INTO source_loads (source, source_url, fetched_on, row_count, note)
           VALUES (:source, :url, :fetched_on, :n, :note)
           RETURNING load_id INTO :out""",
        {
            "source": meta["source"][:60],
            "url": meta["url"][:400],
            "fetched_on": date.fromisoformat(meta["fetched_on"]),
            "n": row_count,
            "note": (note or "")[:400] or None,
            "out": out,
        },
    )
    return int(out.getvalue()[0])


def replace_rows(cur: oracledb.Cursor, table: str, columns: list[str], rows: list[dict], where: str = "") -> None:
    cur.execute(f"DELETE FROM {table} {where}")
    if not rows:
        return
    cols = ", ".join(columns)
    binds = ", ".join(f":{c}" for c in columns)
    cur.executemany(f"INSERT INTO {table} ({cols}) VALUES ({binds})", [{c: r.get(c) for c in columns} for r in rows])


def to_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            continue
    return None


def to_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def to_num(value: Any) -> float | None:
    if value in (None, "", "n/a"):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def clip(value: str | None, n: int) -> str | None:
    if value is None:
        return None
    return value[:n]
