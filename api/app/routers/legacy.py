"""Coexistence path: FastAPI calling the retained APEX-era PL/SQL package unchanged.

During a strangler-fig migration some pages still run their PL/SQL. Exposing that
package here lets the new front end render the *legacy* result next to the new one,
and lets tests prove the two agree before a page is retired.
"""

from fastapi import APIRouter, Depends, HTTPException

from app import db
from app.auth import User, current_user, require_org_access

router = APIRouter(prefix="/v1/legacy", tags=["legacy (PL/SQL coexistence)"])


@router.get("/district-dashboard/{org_code}", summary="emt_legacy.district_dashboard via SYS_REFCURSOR")
def legacy_district_dashboard(org_code: str, user: User = Depends(current_user)) -> dict:
    org_code = org_code.upper()
    if db.query_one("SELECT 1 AS x FROM organizations WHERE code = :c", c=org_code) is None:
        raise HTTPException(404, f"Unknown organization {org_code}")
    require_org_access(user, org_code)
    rows = db.call_refcursor("emt_legacy.district_dashboard(:org)", org=org_code)
    for r in rows:
        r["business_lines"] = [
            {"business_line": bl, "amount": float(amt)}
            for bl, amt in (part.split(":") for part in (r.pop("business_lines") or "").split(",") if part)
        ]
    return {"org_code": org_code, "implementation": "PL/SQL emt_legacy.district_dashboard", "projects": rows}


@router.get("/status-label", summary="emt_legacy.project_status_label evaluated in the database")
def legacy_status_label(
    fy2024: float | None = None, fy2025: float | None = None, user: User = Depends(current_user)
) -> dict:
    row = db.query_one("SELECT emt_legacy.project_status_label(:a, :b) AS label FROM dual", a=fy2024, b=fy2025)
    return {"fy2024": fy2024, "fy2025": fy2025, "label": row["label"], "implementation": "PL/SQL"}
