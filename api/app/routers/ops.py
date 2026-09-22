from fastapi import APIRouter, Depends, Query

from app import db, services
from app.auth import User, current_user, require_org_access
from app.models import LockObservation, NavNotice

router = APIRouter(prefix="/v1/ops", tags=["operations"])


@router.get("/locks", response_model=list[LockObservation], summary="LPMS lock status snapshot (Corps Locks ORDS feed)")
def locks(
    river: str | None = Query(None, description="LPMS river code: MI, OH, IL, TN, CU"),
    user: User = Depends(current_user),
) -> list[LockObservation]:
    pred, binds = "1 = 1", {}
    if river:
        pred, binds = "river_code = :r", {"r": river.upper()}
    rows = db.query(
        f"SELECT * FROM lock_observations WHERE {pred} ORDER BY river_code, lock_mile DESC NULLS LAST", **binds
    )
    return [LockObservation(**r) for r in rows]


@router.get("/rivers", summary="Rivers present in the lock snapshot")
def rivers(user: User = Depends(current_user)) -> list[dict]:
    return db.query(
        """SELECT river_code, MIN(river_name) AS river_name, COUNT(*) AS locks,
                  SUM(pending_arrivals) AS pending_arrivals, ROUND(AVG(avg_delay_24h_min), 1) AS avg_delay_24h_min
             FROM lock_observations GROUP BY river_code ORDER BY river_code"""
    )


@router.get("/notices", response_model=list[NavNotice], summary="NTNI navigation notices by district")
def notices(
    org: str | None = Query(None, description="District code, e.g. MVP"),
    limit: int = Query(100, le=1000),
    user: User = Depends(current_user),
) -> list[NavNotice]:
    if org:
        require_org_access(user, org.upper())
    pred, binds = services.org_scope(user, org.upper() if org else None)
    rows = db.query(
        f"SELECT * FROM nav_notices WHERE {pred} ORDER BY issue_date DESC NULLS LAST"
        f" FETCH FIRST {int(limit)} ROWS ONLY",
        **binds,
    )
    return [NavNotice(**n) for n in rows]
