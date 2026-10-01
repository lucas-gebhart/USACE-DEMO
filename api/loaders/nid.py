"""National Inventory of Dams subset -> assets (BUILDER / facility-status proxy)."""

import csv
from pathlib import Path

import oracledb

from loaders.common import clip, read_json, record_load, replace_rows, to_date, to_num

COLUMNS = [
    "nid_id", "name", "org_code", "owner_names", "primary_owner_type", "primary_purpose", "purposes", "latitude",
    "longitude", "state", "county", "river", "dam_type", "nid_height_ft", "dam_length_ft", "year_completed",
    "nid_storage_af", "drainage_sq_mi", "lock_count", "last_inspection", "inspection_freq_yr", "hazard",
    "condition", "condition_date", "eap_status", "website_url", "load_id",
]  # fmt: skip


def load(cur: oracledb.Cursor, data_dir: Path) -> int:
    meta = read_json(data_dir / "fixtures" / "nid" / "_meta.json")
    cur.execute("SELECT nid_owner_name, code FROM organizations WHERE nid_owner_name IS NOT NULL")
    owner_to_org = {owner: code for owner, code in cur}

    with (data_dir / "fixtures" / "nid" / "dams.csv").open(newline="") as f:
        raw = list(csv.DictReader(f))
    load_id = record_load(
        cur, meta, len(raw), f"NID data last updated {meta.get('data_last_updated')}; {meta.get('selection')}"
    )

    def year(v: str) -> int | None:
        n = to_num(v)
        return int(n) if n and 1000 < n < 2100 else None

    rows, seen = [], set()
    for d in raw:
        nid_id = d["NID ID"]
        if nid_id in seen:
            continue
        seen.add(nid_id)
        owner = d.get("Owner Names") or ""
        org = next((code for name, code in owner_to_org.items() if owner.startswith(name)), None)
        freq = to_num(d.get("Inspection Frequency"))
        rows.append(
            {
                "nid_id": nid_id,
                "name": clip(d["Dam Name"], 200),
                "org_code": org,
                "owner_names": clip(owner, 400),
                "primary_owner_type": clip(d.get("Primary Owner Type"), 40),
                "primary_purpose": clip(d.get("Primary Purpose"), 60),
                "purposes": clip(d.get("Purposes"), 200),
                "latitude": to_num(d.get("Latitude")),
                "longitude": to_num(d.get("Longitude")),
                "state": clip(d.get("State"), 40),
                "county": clip(d.get("County"), 80),
                "river": clip(d.get("River or Stream Name"), 120),
                "dam_type": clip(d.get("Primary Dam Type"), 60),
                "nid_height_ft": to_num(d.get("NID Height (Ft)")),
                "dam_length_ft": to_num(d.get("Dam Length (Ft)")),
                "year_completed": year(d.get("Year Completed") or ""),
                "nid_storage_af": to_num(d.get("NID Storage (Acre-Ft)")),
                "drainage_sq_mi": to_num(d.get("Drainage Area (Sq Miles)")),
                "lock_count": to_num(d.get("Number of Locks")),
                "last_inspection": to_date(d.get("Last Inspection Date")),
                "inspection_freq_yr": int(freq) if freq is not None else None,
                "hazard": clip(d.get("Hazard Potential Classification") or None, 20),
                "condition": clip(d.get("Condition Assessment") or "Not Available", 20),
                "condition_date": to_date(d.get("Condition Assessment Date")),
                "eap_status": clip(d.get("EAP Prepared") or None, 20),
                "website_url": clip(d.get("Website URL") or None, 400),
                "load_id": load_id,
            }
        )
    replace_rows(cur, "assets", COLUMNS, rows)
    return len(rows)
