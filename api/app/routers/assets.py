from fastapi import APIRouter, Depends, Query

from app import db, services
from app.auth import User, current_user, require_org_access
from app.models import Asset

router = APIRouter(prefix="/v1/assets", tags=["assets"])


@router.get(
    "", response_model=list[Asset], summary="National Inventory of Dams subset (BUILDER / facility-status proxy)"
)
def list_assets(
    org: str | None = Query(None, description="Restrict to an org subtree, e.g. MVD or MVP"),
    state: str | None = Query(None, description="Full state name as NID records it, e.g. Minnesota"),
    hazard: str | None = Query(None),
    condition: str | None = Query(None),
    usace_only: bool = Query(True, description="False adds high-hazard non-USACE dams kept as regional context"),
    limit: int = Query(200, le=2000),
    user: User = Depends(current_user),
) -> list[Asset]:
    if org:
        require_org_access(user, org.upper())
    pred, binds = services.org_scope(user, org.upper() if org else None)
    if usace_only:
        pred += " AND org_code IS NOT NULL"
    for col, val in (("state", state), ("hazard", hazard), ("condition", condition)):
        if val:
            pred += f" AND UPPER({col}) = UPPER(:{col})"
            binds[col] = val
    rows = db.query(
        f"SELECT * FROM assets WHERE {pred} ORDER BY hazard, nid_storage_af DESC NULLS LAST"
        f" FETCH FIRST {int(limit)} ROWS ONLY",
        **binds,
    )
    return [Asset(**a) for a in rows]
