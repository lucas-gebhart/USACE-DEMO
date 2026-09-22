"""USAspending fixtures -> agency budget years, federal accounts, program activities, object classes, contracts."""

from pathlib import Path

import oracledb

from loaders.common import clip, read_json, record_load, replace_rows, to_date

CONTRACT_COLUMNS = [
    "piid", "org_code", "recipient_name", "description", "start_date", "end_date", "award_amount",
    "total_outlays", "award_type", "pop_state", "naics_code", "naics_desc", "psc_code", "psc_desc",
    "usaspending_id", "load_id",
]  # fmt: skip


def load_budget(cur: oracledb.Cursor, data_dir: Path) -> int:
    doc = read_json(data_dir / "fixtures" / "usaspending" / "budgetary_resources.json")
    years = doc["agency_data_by_year"]
    load_id = record_load(cur, doc["_meta"], len(years), "agency 096 Corps of Engineers - Civil Works")
    cur.execute("DELETE FROM agency_obligations_by_period")
    cur.execute("DELETE FROM agency_budget_years")
    cur.executemany(
        """INSERT INTO agency_budget_years (fiscal_year, budgetary_resources, obligations, outlays, load_id)
           VALUES (:fy, :res, :obl, :out, :load_id)""",
        [
            {
                "fy": y["fiscal_year"],
                "res": y["agency_budgetary_resources"],
                "obl": y["agency_total_obligated"],
                "out": y["agency_total_outlayed"],
                "load_id": load_id,
            }
            for y in years
        ],
    )
    cur.executemany(
        "INSERT INTO agency_obligations_by_period (fiscal_year, period, obligated) VALUES (:fy, :p, :o)",
        [
            {"fy": y["fiscal_year"], "p": p["period"], "o": p["obligated"]}
            for y in years
            for p in y.get("agency_obligation_by_period", [])
        ],
    )
    return len(years)


def load_accounts(cur: oracledb.Cursor, data_dir: Path) -> int:
    doc = read_json(data_dir / "fixtures" / "usaspending" / "federal_account.json")
    fy = doc["fiscal_year"]
    load_id = record_load(cur, doc["_meta"], len(doc["results"]))
    rows = [
        {
            "account_code": r["code"],
            "fiscal_year": fy,
            "name": clip(r["name"], 160),
            "obligated": r["obligated_amount"],
            "gross_outlays": r["gross_outlay_amount"],
            "load_id": load_id,
        }
        for r in doc["results"]
    ]
    replace_rows(cur, "federal_accounts", list(rows[0]), rows, f"WHERE fiscal_year = {int(fy)}")
    return len(rows)


def _load_named(cur: oracledb.Cursor, data_dir: Path, fixture: str, table: str) -> int:
    doc = read_json(data_dir / "fixtures" / "usaspending" / fixture)
    fy = doc["fiscal_year"]
    record_load(cur, doc["_meta"], len(doc["results"]))
    rows = [
        {
            "fiscal_year": fy,
            "name": clip(r["name"], 160),
            "obligated": r["obligated_amount"],
            "gross_outlays": r["gross_outlay_amount"],
        }
        for r in doc["results"]
    ]
    replace_rows(cur, table, list(rows[0]), rows, f"WHERE fiscal_year = {int(fy)}")
    return len(rows)


def load_program_activities(cur: oracledb.Cursor, data_dir: Path) -> int:
    return _load_named(cur, data_dir, "program_activity.json", "program_activities")


def load_object_classes(cur: oracledb.Cursor, data_dir: Path) -> int:
    return _load_named(cur, data_dir, "object_class.json", "object_classes")


def load_contracts(cur: oracledb.Cursor, data_dir: Path) -> int:
    doc = read_json(data_dir / "fixtures" / "usaspending" / "district_contracts.json")
    meta = doc["_meta"]
    load_id = record_load(cur, meta, len(doc["results"]), meta.get("filters"))
    seen: set[str] = set()
    rows = []
    for r in doc["results"]:
        piid = r["Award ID"]
        if piid in seen:
            continue
        seen.add(piid)
        rows.append(
            {
                "piid": piid,
                "org_code": r["org_code"],
                "recipient_name": clip(r.get("Recipient Name"), 200),
                "description": clip(r.get("Description"), 4000),
                "start_date": to_date(r.get("Start Date")),
                "end_date": to_date(r.get("End Date")),
                "award_amount": r.get("Award Amount"),
                "total_outlays": r.get("Total Outlays"),
                "award_type": clip(r.get("Contract Award Type"), 60),
                "pop_state": clip(r.get("Place of Performance State Code"), 2),
                "naics_code": clip((r.get("NAICS") or {}).get("code"), 6),
                "naics_desc": clip((r.get("NAICS") or {}).get("description"), 200),
                "psc_code": clip((r.get("PSC") or {}).get("code"), 4),
                "psc_desc": clip((r.get("PSC") or {}).get("description"), 200),
                "usaspending_id": clip(r.get("generated_internal_id"), 120),
                "load_id": load_id,
            }
        )
    replace_rows(cur, "contracts", CONTRACT_COLUMNS, rows)
    return len(rows)


def load(cur: oracledb.Cursor, data_dir: Path) -> dict[str, int]:
    return {
        "agency_budget_years": load_budget(cur, data_dir),
        "federal_accounts": load_accounts(cur, data_dir),
        "program_activities": load_program_activities(cur, data_dir),
        "object_classes": load_object_classes(cur, data_dir),
        "contracts": load_contracts(cur, data_dir),
    }
