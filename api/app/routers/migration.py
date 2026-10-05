"""Strangler-fig control plane: which tier owns each legacy APEX page right now.

The React shell asks this before rendering a page. `APEX` means embed the ORDS-served
APEX page (app 100); `REACT` means render the rewritten page. Flipping a route is a
one-row UPDATE against Oracle, so a page can be migrated live and rolled back just as fast.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app import config, db
from app.auth import User, current_user
from app.models import MigrationRoute, MigrationState, MigrationUpdate

router = APIRouter(prefix="/v1/migration", tags=["migration (APEX -> React)"])

SELECT = """SELECT route_key, title, sort_order, apex_page_id, apex_page_name, react_path, api_routes,
                   implementation, migrated_at, note
              FROM migration_routes"""


def apex_url(page_id: int) -> str:
    return f"{config.APEX_BASE_URL}/f?p={config.APEX_APP_ID}:{page_id}"


def to_route(row: dict) -> MigrationRoute:
    row["api_routes"] = [s.strip() for s in row.pop("api_routes").split(",") if s.strip()]
    return MigrationRoute(apex_url=apex_url(row["apex_page_id"]), **row)


def state() -> MigrationState:
    routes = [to_route(r) for r in db.query(f"{SELECT} ORDER BY sort_order")]
    return MigrationState(
        apex_base_url=config.APEX_BASE_URL,
        apex_app_id=config.APEX_APP_ID,
        apex_builder_url=f"{config.APEX_BASE_URL}/f?p=4000:1:::::FB_FLOW_ID:{config.APEX_APP_ID}",
        routes=routes,
        migrated_count=sum(r.implementation == "REACT" for r in routes),
        total_count=len(routes),
    )


@router.get("", response_model=MigrationState, summary="Every legacy APEX page and which tier owns it")
def get_state(user: User = Depends(current_user)) -> MigrationState:
    return state()


@router.get("/{route_key}", response_model=MigrationRoute, summary="One route's current implementation")
def get_route(route_key: str, user: User = Depends(current_user)) -> MigrationRoute:
    row = db.query_one(f"{SELECT} WHERE route_key = :k", k=route_key)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown route {route_key}")
    return to_route(row)


@router.put("/{route_key}", response_model=MigrationRoute, summary="Flip a page between APEX and React (HQ only)")
def set_route(route_key: str, body: MigrationUpdate, user: User = Depends(current_user)) -> MigrationRoute:
    if user.role != "HQ":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only HQ may change page ownership")
    impl = body.implementation.upper()
    if impl not in ("APEX", "REACT"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "implementation must be APEX or REACT")
    n = db.execute(
        """UPDATE migration_routes
              SET implementation = :impl,
                  migrated_at = CASE WHEN :impl = 'REACT' THEN SYSTIMESTAMP ELSE NULL END
            WHERE route_key = :k""",
        impl=impl,
        k=route_key,
    )
    if n == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown route {route_key}")
    return get_route(route_key, user)
