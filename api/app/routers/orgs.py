from fastapi import APIRouter, Depends, HTTPException

from app import db, services
from app.auth import User, current_user, require_org_access
from app.models import Contract, DistrictDashboard, NavNotice, Org, OrgRollup, ProjectSummary

router = APIRouter(prefix="/v1/orgs", tags=["orgs"])


@router.get("", response_model=OrgRollup, summary="Org tree with rollups, rooted at the caller's organization")
def org_tree(user: User = Depends(current_user)) -> OrgRollup:
    return services.rollup_tree(user.org_code)


@router.get("/{org_code}", response_model=DistrictDashboard, summary="District / division dashboard")
def district_dashboard(org_code: str, user: User = Depends(current_user)) -> DistrictDashboard:
    """Replaces the APEX page-20 process in db/legacy/apex_page_process_example.sql.

    Same Oracle tables, but: authorization is a token claim instead of session state,
    the status label is versioned Python (`services.project_status_label`), and the
    result is a typed JSON document any client can render.
    """
    org_code = org_code.upper()
    org = db.query_one(
        "SELECT code, name, kind, parent_code, dodaac_prefix, states FROM organizations WHERE code = :c", c=org_code
    )
    if org is None:
        raise HTTPException(404, f"Unknown organization {org_code}")
    require_org_access(user, org_code)
    scope = services.org_scope(user, org_code)
    pred, binds = scope
    projects = services.with_status(
        db.query(
            f"""SELECT project_id, name, state, org_code, district_name, division_name, fy2023_allocation,
                       fy2024_assumed, fy2024_iija, fy2025_maintenance, fy2025_operations, fy2025_total
                  FROM projects WHERE {pred} ORDER BY fy2025_total DESC NULLS LAST""",
            **binds,
        )
    )
    contracts = services.with_award_url(
        db.query(
            f"SELECT * FROM contracts WHERE {pred} ORDER BY award_amount DESC NULLS LAST FETCH FIRST 25 ROWS ONLY",
            **binds,
        )
    )
    notices = db.query(
        f"SELECT * FROM nav_notices WHERE {pred} ORDER BY issue_date DESC FETCH FIRST 25 ROWS ONLY", **binds
    )
    return DistrictDashboard(
        org=Org(**org),
        rollup=services.rollup_tree(org_code),
        hazard_mix=services.mix(scope, "hazard"),
        condition_mix=services.mix(scope, "condition"),
        projects=[ProjectSummary(**p) for p in projects],
        contracts=[Contract(**c) for c in contracts],
        notices=[NavNotice(**n) for n in notices],
        sources=services.sources(),
    )
