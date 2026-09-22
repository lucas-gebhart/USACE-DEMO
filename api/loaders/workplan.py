"""FY2025 O&M justification sheets -> projects + project_business_lines (P2/work-plan proxy)."""

from pathlib import Path

import oracledb

from loaders.common import clip, read_json, record_load
from loaders.orgs import district_lookup


def load(cur: oracledb.Cursor, data_dir: Path) -> int:
    doc = read_json(data_dir / "fixtures" / "workplan" / "fy2025_om_jsheets.json")
    meta = doc["_meta"]
    projects = doc["projects"]
    load_id = record_load(cur, meta, len(projects), meta.get("note"))
    districts = district_lookup(cur)

    cur.execute("DELETE FROM project_business_lines")
    cur.execute("DELETE FROM projects")
    pid = cur.var(oracledb.DB_TYPE_NUMBER)
    for p in projects:
        cur.execute(
            """INSERT INTO projects (name, state, org_code, division_name, district_name, authorization, description,
                                     fy2023_allocation, fy2024_assumed, fy2024_iija, fy2025_maintenance,
                                     fy2025_operations, fy2025_total, source_page, load_id)
               VALUES (:name, :state, :org_code, :division_name, :district_name, :authorization, :description,
                       :fy23, :fy24, :iija, :maint, :ops, :total, :page, :load_id)
               RETURNING project_id INTO :pid""",
            {
                "name": clip(p["project_name"], 200),
                "state": clip(p.get("state"), 40),
                "org_code": districts.get((p.get("district") or "").lower()),
                "division_name": clip(p.get("division"), 80),
                "district_name": clip(p.get("district"), 80),
                "authorization": clip(p.get("authorization"), 2000),
                "description": clip(p.get("description"), 4000),
                "fy23": p.get("fy2023_allocation"),
                "fy24": p.get("fy2024_assumed_allocation"),
                "iija": p.get("fy2024_iija"),
                "maint": p.get("fy2025_maintenance"),
                "ops": p.get("fy2025_operations"),
                "total": p.get("fy2025_total"),
                "page": p.get("pdf_page"),
                "load_id": load_id,
                "pid": pid,
            },
        )
        project_id = int(pid.getvalue()[0])
        lines = [
            {"project_id": project_id, "bl": code, "amt": amount}
            for code, amount in (p.get("business_lines") or {}).items()
            if amount is not None
        ]
        if lines:
            cur.executemany(
                "INSERT INTO project_business_lines (project_id, business_line, amount)"
                " VALUES (:project_id, :bl, :amt)",
                lines,
            )
    return len(projects)
