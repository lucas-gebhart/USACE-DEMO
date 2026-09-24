from fastapi import APIRouter, Depends, Query

from app import db, services
from app.auth import User, current_user, require_org_access
from app.models import Contract

router = APIRouter(prefix="/v1/contracts", tags=["contracts"])


@router.get("", response_model=list[Contract], summary="Department of the Army awards by district DoDAAC (CEFMS proxy)")
def list_contracts(
    org: str | None = Query(None, description="Restrict to an org subtree, e.g. MVD or MVP"),
    q: str | None = Query(None, description="Search recipient or description"),
    active_on: str | None = Query(None, description="ISO date; only awards whose period of performance covers it"),
    limit: int = Query(100, le=500),
    user: User = Depends(current_user),
) -> list[Contract]:
    if org:
        require_org_access(user, org.upper())
    pred, binds = services.org_scope(user, org.upper() if org else None)
    if q:
        pred += " AND (UPPER(recipient_name) LIKE :q OR UPPER(description) LIKE :q)"
        binds["q"] = f"%{q.upper()}%"
    if active_on:
        pred += " AND start_date <= TO_DATE(:d, 'YYYY-MM-DD')"
        pred += " AND (end_date IS NULL OR end_date >= TO_DATE(:d, 'YYYY-MM-DD'))"
        binds["d"] = active_on
    rows = db.query(
        f"SELECT * FROM contracts WHERE {pred} ORDER BY award_amount DESC NULLS LAST"
        f" FETCH FIRST {int(limit)} ROWS ONLY",
        **binds,
    )
    return [Contract(**c) for c in services.with_award_url(rows)]
