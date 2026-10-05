from fastapi import APIRouter, Depends

from app import db
from app.auth import User, current_user
from app.models import NamedAmount

router = APIRouter(prefix="/v1/workforce", tags=["workforce"])

PERSONNEL_CLASSES = (
    "Full-time permanent", "Other than full-time permanent", "Other personnel compensation",
    "Civilian personnel benefits", "Benefits for former personnel", "Military personnel benefits",
    "Special personal services payments",
)  # fmt: skip


@router.get("", summary="Workforce proxy: personnel object classes from USAspending; no labor-log data is public")
def workforce(user: User = Depends(current_user)) -> dict:
    fy = db.query_one("SELECT MAX(fiscal_year) AS fy FROM object_classes")["fy"]
    binds = {f"c{i}": c for i, c in enumerate(PERSONNEL_CLASSES)}
    rows = db.query(
        "SELECT name, obligated, gross_outlays FROM object_classes WHERE fiscal_year = :fy AND name IN ("
        + ", ".join(f":{k}" for k in binds)
        + ") ORDER BY obligated DESC",
        fy=fy,
        **binds,
    )
    total = db.query_one("SELECT SUM(obligated) AS t FROM object_classes WHERE fiscal_year = :fy", fy=fy)["t"]
    personnel = sum(r["obligated"] or 0 for r in rows)
    return {
        "fiscal_year": fy,
        "personnel_object_classes": [NamedAmount(**r) for r in rows],
        "personnel_obligated": personnel,
        "total_obligated": total,
        "personnel_share": round(personnel / total, 4) if total else None,
        "caveat": (
            "EMS labor logs are internal. This view uses USAspending object-class obligations for agency 096 as a "
            "compensation proxy; OPM FedScope (data.opm.gov) can add headcount by agency/occupation offline. "
            "Project-level labor allocation would come from EMS/CEFMS inside the enclave."
        ),
    }
