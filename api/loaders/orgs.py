import csv
from pathlib import Path

import oracledb

COLUMNS = ["code", "name", "kind", "parent_code", "dodaac_prefix", "nid_owner_name", "states"]


def read_orgs(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return [{k: (v or None) for k, v in row.items()} for row in csv.DictReader(f)]


def load(cur: oracledb.Cursor, data_dir: Path) -> int:
    rows = read_orgs(data_dir / "reference" / "orgs.csv")
    cur.execute("SELECT COUNT(*) FROM organizations")
    if cur.fetchone()[0]:
        cur.executemany(
            "UPDATE organizations SET name=:name, kind=:kind, parent_code=:parent_code, dodaac_prefix=:dodaac_prefix,"
            " nid_owner_name=:nid_owner_name, states=:states WHERE code=:code",
            rows,
        )
        known = {r[0] for r in cur.execute("SELECT code FROM organizations")}
        rows = [r for r in rows if r["code"] not in known]
    # parents first: HQ, then divisions, then districts
    order = {"HQ": 0, "DIVISION": 1, "DISTRICT": 2}
    rows.sort(key=lambda r: order[r["kind"]])
    if rows:
        cols = ", ".join(COLUMNS)
        binds = ", ".join(f":{c}" for c in COLUMNS)
        cur.executemany(f"INSERT INTO organizations ({cols}) VALUES ({binds})", rows)
    return len(rows)


def district_lookup(cur: oracledb.Cursor) -> dict[str, str]:
    """'st. paul' -> 'MVP', built from organizations.name minus the word District."""
    cur.execute("SELECT code, name FROM organizations WHERE kind = 'DISTRICT'")
    return {name.lower().replace(" district", "").strip(): code for code, name in cur}
