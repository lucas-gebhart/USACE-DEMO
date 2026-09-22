"""Public-fixture loaders. `python -m loaders` migrates and loads everything into Oracle."""

from __future__ import annotations

import logging
from pathlib import Path

import oracledb

from app import config
from app.migrate import apply_migrations
from loaders import nid, ops, orgs, usaspending, workplan

log = logging.getLogger(__name__)


def load_all(conn: oracledb.Connection, data_dir: Path = config.DATA_DIR) -> dict[str, int]:
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        counts["organizations"] = orgs.load(cur, data_dir)
        counts.update(usaspending.load(cur, data_dir))
        counts["projects"] = workplan.load(cur, data_dir)
        counts["assets"] = nid.load(cur, data_dir)
        counts.update(ops.load(cur, data_dir))
    conn.commit()
    return counts


def migrate_and_load(conn: oracledb.Connection) -> dict[str, int]:
    applied = apply_migrations(conn)
    log.info("migrations applied: %s", applied or "none")
    counts = load_all(conn)
    log.info("loaded: %s", counts)
    return counts
