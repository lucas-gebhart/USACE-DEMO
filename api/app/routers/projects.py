from fastapi import APIRouter, Depends, HTTPException, Query

from app import db, services
from app.auth import User, current_user, require_org_access
from app.models import Asset, BusinessLine, Contract, Project, ProjectSummary, SourceLoad

router = APIRouter(prefix="/v1/projects", tags=["projects"])

SUMMARY_COLS = """project_id, name, state, org_code, district_name, division_name, fy2023_allocation, fy2024_assumed,
                  fy2024_iija, fy2025_maintenance, fy2025_operations, fy2025_total"""


@router.get("", response_model=list[ProjectSummary], summary="FY2025 O&M work-plan projects (P2 proxy)")
def list_projects(
    org: str | None = Query(None, description="Restrict to an org subtree, e.g. MVD or MVP"),
    q: str | None = Query(None, description="Case-insensitive name search"),
    status: str | None = Query(None, pattern="^(GROWING|SHRINKING|STEADY|UNKNOWN)$"),
    limit: int = Query(100, le=500),
    user: User = Depends(current_user),
) -> list[ProjectSummary]:
    if org:
        require_org_access(user, org.upper())
    pred, binds = services.org_scope(user, org.upper() if org else None)
    if q:
        pred += " AND UPPER(name) LIKE :q"
        binds["q"] = f"%{q.upper()}%"
    rows = services.with_status(
        db.query(f"SELECT {SUMMARY_COLS} FROM projects WHERE {pred} ORDER BY fy2025_total DESC NULLS LAST", **binds)
    )
    if status:
        rows = [r for r in rows if r["status_label"] == status]
    return [ProjectSummary(**r) for r in rows[:limit]]


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: int, user: User = Depends(current_user)) -> Project:
    row = db.query_one("SELECT * FROM projects WHERE project_id = :id", id=project_id)
    if row is None:
        raise HTTPException(404, "Project not found")
    if row["org_code"]:
        require_org_access(user, row["org_code"])
    services.with_status([row])
    lines = db.query(
        "SELECT business_line, amount FROM project_business_lines WHERE project_id = :id ORDER BY amount DESC",
        id=project_id,
    )
    source = (
        db.query_one("SELECT * FROM source_loads WHERE load_id = :l", l=row["load_id"]) if row.get("load_id") else None
    )
    return Project(
        **row, business_lines=[BusinessLine(**b) for b in lines], source=SourceLoad(**source) if source else None
    )


@router.get("/{project_id}/related", summary="Same-district contracts and same-state assets (public-data linkage)")
def related(project_id: int, user: User = Depends(current_user)) -> dict:
    row = db.query_one("SELECT org_code, state, name FROM projects WHERE project_id = :id", id=project_id)
    if row is None:
        raise HTTPException(404, "Project not found")
    if row["org_code"]:
        require_org_access(user, row["org_code"])
    # Public award data has no project key, so linkage is heuristic: keyword match on the project's leading words
    # within the same district, then any same-district awards.
    keyword = row["name"].split(",")[0].split(" ")[0].upper()
    contracts = services.with_award_url(
        db.query(
            """SELECT * FROM contracts WHERE org_code = :o
               ORDER BY CASE WHEN UPPER(description) LIKE :kw THEN 0 ELSE 1 END, award_amount DESC NULLS LAST
               FETCH FIRST 10 ROWS ONLY""",
            o=row["org_code"],
            kw=f"%{keyword}%",
        )
    )
    assets = db.query(
        """SELECT * FROM assets WHERE org_code = :o AND UPPER(state) = UPPER(:st)
           ORDER BY CASE WHEN UPPER(name) LIKE :kw THEN 0 ELSE 1 END, nid_storage_af DESC NULLS LAST
           FETCH FIRST 10 ROWS ONLY""",
        o=row["org_code"],
        st=_state_name(row["state"]),
        kw=f"%{keyword}%",
    )
    return {
        "match_basis": f"district {row['org_code']}, keyword '{keyword}', state {row['state']}",
        "contracts": [Contract(**c) for c in contracts],
        "assets": [Asset(**a) for a in assets],
    }


STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia", "PR": "Puerto Rico",
}  # fmt: skip


def _state_name(abbr: str | None) -> str:
    """J-sheets carry postal codes ("MN", sometimes "MN & WI"); NID carries full names."""
    if not abbr:
        return ""
    return STATES.get(abbr.split(" ")[0].split(",")[0].strip().upper(), abbr)
