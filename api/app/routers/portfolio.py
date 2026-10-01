from fastapi import APIRouter, Depends

from app import db, services
from app.auth import User, current_user
from app.models import BudgetYear, FederalAccount, NamedAmount, Org, Portfolio

router = APIRouter(prefix="/v1", tags=["portfolio"])


@router.get("/portfolio", response_model=Portfolio, summary="Enterprise / program-level view for the caller's scope")
def portfolio(user: User = Depends(current_user)) -> Portfolio:
    scope = services.org_scope(user)
    org = db.query_one(
        "SELECT code, name, kind, parent_code, dodaac_prefix, states FROM organizations WHERE code = :c",
        c=user.org_code,
    )
    years = db.query("SELECT * FROM agency_budget_years ORDER BY fiscal_year DESC")
    periods = db.query(
        "SELECT fiscal_year, period, obligated FROM agency_obligations_by_period ORDER BY fiscal_year, period"
    )
    for y in years:
        y["obligations_by_period"] = [
            {"period": p["period"], "obligated": p["obligated"]}
            for p in periods
            if p["fiscal_year"] == y["fiscal_year"]
        ]
    fy = db.query_one("SELECT MAX(fiscal_year) AS fy FROM federal_accounts")["fy"]
    accounts = db.query(
        "SELECT * FROM federal_accounts WHERE fiscal_year = :fy ORDER BY obligated DESC NULLS LAST", fy=fy
    )
    programs = db.query(
        "SELECT * FROM program_activities WHERE fiscal_year = :fy ORDER BY obligated DESC NULLS LAST", fy=fy
    )
    objects = db.query("SELECT * FROM object_classes WHERE fiscal_year = :fy ORDER BY obligated DESC NULLS LAST", fy=fy)
    locks = db.query_one(
        """SELECT COUNT(*) AS locks_reporting,
                  SUM(pending_arrivals) AS pending_arrivals,
                  SUM(locked_up_24h + locked_down_24h) AS lockages_24h,
                  ROUND(AVG(avg_delay_24h_min), 1) AS avg_delay_24h_min,
                  MAX(reading_at) AS latest_reading
             FROM lock_observations WHERE reading_at IS NOT NULL"""
    )
    return Portfolio(
        scope=Org(**org),
        budget_years=[BudgetYear(**y) for y in years],
        federal_accounts=[FederalAccount(**a) for a in accounts],
        program_activities=[NamedAmount(**p) for p in programs],
        object_classes=[NamedAmount(**o) for o in objects],
        rollup=services.rollup_tree(user.org_code),
        business_line_mix=services.business_line_mix(services.org_scope(user, column="p.org_code")),
        hazard_mix=services.mix(scope, "hazard"),
        condition_mix=services.mix(scope, "condition"),
        lock_summary=locks or {},
        sources=services.sources(),
    )
