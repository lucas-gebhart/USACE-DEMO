"""LPMS lock status + NTNI navigation notices -> lock_observations, nav_notices (operations proxy)."""

import json
from datetime import datetime
from pathlib import Path

import oracledb

from loaders.common import clip, record_load, replace_rows, to_num, to_ts

LOCK_COLUMNS = [
    "river_code", "river_name", "lock_number", "lock_name", "lock_mile", "reading_at", "upper_gage_ft",
    "lower_gage_ft", "pending_arrivals", "locking_now", "locked_up_24h", "locked_down_24h", "avg_delay_24h_min",
    "notes", "load_id",
]  # fmt: skip
NOTICE_COLUMNS = [
    "notice_no",
    "org_code",
    "control_number",
    "issue_date",
    "begin_date",
    "waterways",
    "notice_url",
    "load_id",
]


def lpms_reading(value: str | None) -> datetime | None:
    """LPMS encodes the reading time as MMDDYY:HHMM; unread locks send ':'."""
    if not value or value.strip(": ") == "":
        return None
    try:
        return datetime.strptime(value.strip(), "%m%d%y:%H%M")
    except ValueError:
        return None


def load_locks(cur: oracledb.Cursor, data_dir: Path) -> int:
    rows = []
    cur.execute("DELETE FROM lock_observations")
    for path in sorted((data_dir / "fixtures" / "lpms").glob("lock_status_*.json")):
        doc = json.loads(path.read_text(), strict=False)
        river_code = path.stem.rsplit("_", 1)[1]
        locks = [
            (r.get("riverName"), lk) for r in doc.get("rivers", []) for lk in r.get("locks", []) if "lockName" in lk
        ]
        load_id = record_load(cur, doc["_meta"], len(locks), f"river code {river_code}")
        for river_name, lk in locks:
            rows.append(
                {
                    "river_code": river_code,
                    "river_name": clip(river_name, 80),
                    "lock_number": clip(str(lk.get("lockNumber")), 6),
                    "lock_name": clip(lk.get("lockName"), 80),
                    "lock_mile": to_num(lk.get("lockMile")),
                    "reading_at": lpms_reading(lk.get("readingEntryDateTime")),
                    "upper_gage_ft": to_num(lk.get("gageUpperElevation")),
                    "lower_gage_ft": to_num(lk.get("gageLowerElevation")),
                    "pending_arrivals": to_num(lk.get("totalPendingArrivals")),
                    "locking_now": to_num(lk.get("totalLocking")),
                    "locked_up_24h": to_num(lk.get("totalLockedUp24Hours")),
                    "locked_down_24h": to_num(lk.get("totalLockedDown24Hours")),
                    "avg_delay_24h_min": to_num(lk.get("average24HourDelay")),
                    "notes": clip((lk.get("notes") or "").replace("\r", "\n").strip() or None, 2000),
                    "load_id": load_id,
                }
            )
    if rows:
        cols = ", ".join(LOCK_COLUMNS)
        binds = ", ".join(f":{c}" for c in LOCK_COLUMNS)
        cur.executemany(f"INSERT INTO lock_observations ({cols}) VALUES ({binds})", rows)
    return len(rows)


def load_notices(cur: oracledb.Cursor, data_dir: Path) -> int:
    rows, seen = [], set()
    for path in sorted((data_dir / "fixtures" / "ntni").glob("notices_*.json")):
        doc = json.loads(path.read_text())
        org = path.stem.rsplit("_", 1)[1]
        items = doc.get("items", [])
        load_id = record_load(cur, doc["_meta"], len(items), f"district {org}")
        for n in items:
            notice_no = str(n.get("noticeno") or n.get("controlnumber"))
            if notice_no in seen:
                continue
            seen.add(notice_no)
            rows.append(
                {
                    "notice_no": clip(notice_no, 20),
                    "org_code": org,
                    "control_number": n.get("controlnumber"),
                    "issue_date": to_ts(n.get("issuedate")),
                    "begin_date": to_ts(n.get("begindate")),
                    "waterways": clip(n.get("waterways"), 400),
                    "notice_url": clip(n.get("noticelink"), 400),
                    "load_id": load_id,
                }
            )
    replace_rows(cur, "nav_notices", NOTICE_COLUMNS, rows)
    return len(rows)


def load(cur: oracledb.Cursor, data_dir: Path) -> dict[str, int]:
    return {"lock_observations": load_locks(cur, data_dir), "nav_notices": load_notices(cur, data_dir)}
