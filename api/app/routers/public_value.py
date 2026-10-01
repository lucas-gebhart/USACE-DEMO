"""Public-value metrics: what USACE operations deliver to the public, starting with the
Sustainable Rivers Program (river miles, structures and river systems covered).

Everything here is transcribed from public HEC/ERDC publications (data/fixtures/srp); the
route just shapes it for the React page. Program totals are national; the site roster is
flagged `in_scope` against the caller's org subtree so a division sees its own rivers first.
"""

from collections.abc import Callable

from fastapi import APIRouter, Depends

from app import config, db, services
from app.auth import User, current_user, visible_orgs
from app.models import (
    MixEntry,
    Org,
    PublicValueSrp,
    SrpDivisionCount,
    SrpDocument,
    SrpFootprint,
    SrpMetric,
    SrpSite,
)
from loaders.common import read_json

router = APIRouter(prefix="/v1/public-value", tags=["public value"])

GROUPS = {
    "structures": "STRUCTURES",
    "phase_miles": "PHASE_MILES",
    "action_purpose_miles": "ACTION_PURPOSE_MILES",
    "action_purpose_acres": "ACTION_PURPOSE_ACRES",
    "new_river_proposals": "NEW_RIVER_PROPOSALS",
    "budget_change_pct": "BUDGET_CHANGE_PCT",
}


def _mix(sites: list[SrpSite], key: Callable[[SrpSite], str]) -> list[MixEntry]:
    counts: dict[str, int] = {}
    for s in sites:
        counts[key(s)] = counts.get(key(s), 0) + 1
    return [MixEntry(label=k, count=v) for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]


@router.get(
    "/srp", response_model=PublicValueSrp, summary="Sustainable Rivers Program: miles, structures and systems covered"
)
def sustainable_rivers(user: User = Depends(current_user)) -> PublicValueSrp:
    org = db.query_one("SELECT * FROM organizations WHERE code = :c", c=user.org_code)
    scope = visible_orgs(user.org_code)
    hq = user.org_code == "HQ"

    metrics = [SrpMetric(**r) for r in db.query("SELECT * FROM srp_metrics ORDER BY metric_group, sort_order")]
    by_group = {name: [m for m in metrics if m.metric_group == grp] for name, grp in GROUPS.items()}

    sites = [
        SrpSite(**r, in_scope=hq or r["org_code"] in scope)
        for r in db.query("SELECT * FROM v_emt_srp_sites ORDER BY start_year, site_name")
    ]
    divisions = db.query("SELECT code, name FROM organizations WHERE kind = 'DIVISION' ORDER BY code")
    by_division = [
        SrpDivisionCount(
            code=d["code"],
            name=d["name"],
            sites=sum(s.division_code == d["code"] for s in sites),
            implementing=sum(s.division_code == d["code"] and s.phase != "Advance" for s in sites),
            in_scope=hq or d["code"] in scope,
        )
        for d in divisions
    ]

    documents = read_json(config.DATA_DIR / "fixtures" / "srp" / "sustainable_rivers.json")["_meta"]["documents"]
    return PublicValueSrp(
        scope=Org(**org),
        footprint=[SrpFootprint(**r) for r in db.query("SELECT * FROM srp_footprint ORDER BY as_of_year")],
        **by_group,
        sites=sites,
        by_division=[d for d in by_division if d.sites],
        infrastructure_mix=_mix(sites, lambda s: s.infrastructure_label),
        phase_mix=_mix(sites, lambda s: s.phase),
        documents=[SrpDocument(**d) for d in documents],
        sources=[s for s in services.sources() if s.source.startswith("Sustainable Rivers")],
    )
