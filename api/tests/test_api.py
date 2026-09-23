from datetime import date

import pytest

from app.services import project_status_label


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["database"] == "FREEPDB1"


def test_openapi_lists_v1_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in ("/v1/portfolio", "/v1/orgs/{org_code}", "/v1/projects", "/v1/contracts", "/v1/assets", "/v1/ops/locks",
              "/v1/workforce", "/v1/legacy/district-dashboard/{org_code}", "/v1/sources", "/v1/migration"):  # fmt: skip
        assert p in paths


# --- auth / role scoping -----------------------------------------------------


def test_requires_bearer(client):
    assert client.get("/v1/portfolio").status_code == 401
    assert client.get("/v1/portfolio", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_bad_password(client):
    assert client.post("/auth/token", json={"username": "hq.analyst", "password": "wrong"}).status_code == 401


def test_token_claims(client, mvp):
    me = client.get("/auth/me", headers=mvp).json()
    assert me == {"username": "mvp.pm", "display_name": "St. Paul District PM", "role": "DISTRICT", "org_code": "MVP"}


def test_district_cannot_see_sibling(client, mvp):
    assert client.get("/v1/orgs/MVP", headers=mvp).status_code == 200
    assert client.get("/v1/orgs/MVS", headers=mvp).status_code == 403
    assert client.get("/v1/orgs/MVD", headers=mvp).status_code == 403
    assert client.get("/v1/projects?org=MVS", headers=mvp).status_code == 403


def test_division_sees_its_districts_only(client, mvd):
    assert client.get("/v1/orgs/MVP", headers=mvd).status_code == 200
    assert client.get("/v1/orgs/MVS", headers=mvd).status_code == 200
    assert client.get("/v1/orgs/LRH", headers=mvd).status_code == 403
    codes = {p["org_code"] for p in client.get("/v1/projects?limit=500", headers=mvd).json()}
    assert codes <= {"MVP", "MVR", "MVS", "MVM", "MVK", "MVN"}
    assert len(codes) >= 5


def test_hq_sees_everything(client, hq):
    tree = client.get("/v1/orgs", headers=hq).json()
    assert tree["code"] == "HQ"
    assert {c["code"] for c in tree["children"]} == {"LRD", "MVD", "NAD", "NWD", "POD", "SAD", "SPD", "SWD"}
    assert tree["project_count"] == 409
    assert tree["fy2025_budget"] == pytest.approx(2_207_067_000)
    assert client.get("/v1/orgs/LRH", headers=hq).status_code == 200


def test_unknown_org_404(client, hq):
    assert client.get("/v1/orgs/ZZZ", headers=hq).status_code == 404


# --- portfolio / org rollups -------------------------------------------------


def test_portfolio_enterprise(client, hq):
    p = client.get("/v1/portfolio", headers=hq).json()
    fy25 = next(y for y in p["budget_years"] if y["fiscal_year"] == 2025)
    assert fy25["budgetary_resources"] > 50e9
    assert fy25["obligations_by_period"]
    assert any(a["account_code"] == "096-3123" for a in p["federal_accounts"])  # O&M, Corps of Engineers-Civil
    assert {m["business_line"] for m in p["business_line_mix"]} <= {"ENS", "FRM", "HYD", "NAV", "REC", "WTR"}
    # HQ's mix includes the non-USACE high-hazard context dams, so it exceeds the USACE-owned rollup count
    hazard_total = sum(m["count"] for m in p["hazard_mix"])
    assert hazard_total > p["rollup"]["asset_count"]
    assert hazard_total == sum(m["count"] for m in p["condition_mix"])
    assert p["lock_summary"]["locks_reporting"] > 0
    assert {s["source"] for s in p["sources"]} >= {"USAspending", "National Inventory of Dams"}


def test_portfolio_is_scoped_for_district(client, mvp):
    p = client.get("/v1/portfolio", headers=mvp).json()
    assert p["scope"]["code"] == "MVP"
    assert p["rollup"]["project_count"] == 11
    assert sum(m["count"] for m in p["hazard_mix"]) == p["rollup"]["asset_count"]


def test_division_rollup_sums_children(client, mvd):
    tree = client.get("/v1/orgs", headers=mvd).json()
    assert tree["project_count"] == sum(c["project_count"] for c in tree["children"])
    assert tree["fy2025_budget"] == pytest.approx(sum(c["fy2025_budget"] for c in tree["children"]))


def test_district_dashboard(client, mvp):
    d = client.get("/v1/orgs/MVP", headers=mvp).json()
    assert d["org"]["dodaac_prefix"] == "W912ES"
    assert d["rollup"]["project_count"] == len(d["projects"]) == 11
    names = [p["name"] for p in d["projects"]]
    assert any("Mississippi River" in n for n in names)
    assert d["projects"] == sorted(d["projects"], key=lambda p: -(p["fy2025_total"] or 0))
    assert all(c["org_code"] == "MVP" for c in d["contracts"])
    assert all(n["org_code"] == "MVP" for n in d["notices"])
    assert {p["status_label"] for p in d["projects"]} <= {"GROWING", "SHRINKING", "STEADY", "UNKNOWN"}


# --- projects / contracts / assets / ops -------------------------------------


def test_project_detail_and_related(client, mvp):
    projects = client.get("/v1/projects?q=headwaters", headers=mvp).json()
    assert len(projects) == 1
    pid = projects[0]["project_id"]
    p = client.get(f"/v1/projects/{pid}", headers=mvp).json()
    assert p["name"].startswith("Reservoirs at Headwaters of Mississippi River")
    assert {b["business_line"] for b in p["business_lines"]} == {"FRM", "REC", "ENS"}
    assert sum(b["amount"] for b in p["business_lines"]) == p["fy2025_total"]
    assert p["source"]["source_url"].startswith("https://")
    rel = client.get(f"/v1/projects/{pid}/related", headers=mvp).json()
    assert all(c["org_code"] == "MVP" for c in rel["contracts"])
    assert all(a["state"] == "Minnesota" for a in rel["assets"])


def test_project_status_filter(client, hq):
    growing = client.get("/v1/projects?status=GROWING&limit=500", headers=hq).json()
    assert growing and all(p["status_label"] == "GROWING" for p in growing)
    assert all(p["fy2025_total"] >= p["fy2024_assumed"] * 1.10 for p in growing)


def test_contracts_search_and_active_window(client, mvp):
    rows = client.get("/v1/contracts?limit=5", headers=mvp).json()
    assert len(rows) == 5 and all(r["org_code"] == "MVP" for r in rows)
    assert all(
        r["usaspending_url"].startswith("https://www.usaspending.gov/award/") for r in rows if r["usaspending_id"]
    )
    active = client.get("/v1/contracts?active_on=2025-06-30", headers=mvp).json()
    for r in active:
        assert date.fromisoformat(r["start_date"]) <= date(2025, 6, 30)
        assert r["end_date"] is None or date.fromisoformat(r["end_date"]) >= date(2025, 6, 30)


def test_assets_filters(client, hq):
    usace = client.get("/v1/assets?org=MVP", headers=hq).json()
    assert usace and all(a["org_code"] == "MVP" for a in usace)
    high = client.get("/v1/assets?hazard=High&state=Minnesota&usace_only=false", headers=hq).json()
    assert high and all(a["hazard"] == "High" and a["state"] == "Minnesota" for a in high)
    assert any(a["org_code"] is None for a in high)  # regional context dams present for HQ


def test_ops(client, mvp):
    locks = client.get("/v1/ops/locks?river=MI", headers=mvp).json()
    assert locks and all(lk["river_code"] == "MI" for lk in locks)
    assert any(lk["reading_at"] for lk in locks)
    rivers = {r["river_code"] for r in client.get("/v1/ops/rivers", headers=mvp).json()}
    assert {"MI", "OH", "IL", "TN", "CU"} <= rivers
    notices = client.get("/v1/ops/notices", headers=mvp).json()
    assert notices and all(n["org_code"] == "MVP" for n in notices)
    assert all(n["notice_url"].startswith("https://ndc.ops.usace.army.mil/") for n in notices)


def test_workforce_is_labelled_as_proxy(client, hq):
    w = client.get("/v1/workforce", headers=hq).json()
    assert w["personnel_obligated"] > 0 and 0 < w["personnel_share"] < 1
    assert "EMS labor logs are internal" in w["caveat"]


def test_sources_lineage(client, hq):
    sources = client.get("/v1/sources", headers=hq).json()
    by_source = {s["source"]: s for s in sources}
    assert by_source["National Inventory of Dams"]["row_count"] > 3000
    assert all(s["fetched_on"] and s["loaded_at"] for s in sources)


# --- legacy PL/SQL coexistence -----------------------------------------------


@pytest.mark.parametrize(
    ("fy24", "fy25", "label"),
    [
        (None, 5, "UNKNOWN"),
        (0, 5, "UNKNOWN"),
        (100, None, "UNKNOWN"),
        (100, 110, "GROWING"),
        (100, 109.99, "STEADY"),
        (100, 90, "SHRINKING"),
        (100, 90.01, "STEADY"),
    ],
)
def test_status_label_python_matches_plsql(client, hq, fy24, fy25, label):
    assert project_status_label(fy24, fy25) == label
    q = "&".join(f"{k}={v}" for k, v in (("fy2024", fy24), ("fy2025", fy25)) if v is not None)
    assert client.get(f"/v1/legacy/status-label?{q}", headers=hq).json()["label"] == label


def test_legacy_dashboard_matches_new_route(client, mvp):
    new = client.get("/v1/orgs/MVP", headers=mvp).json()["projects"]
    old = client.get("/v1/legacy/district-dashboard/MVP", headers=mvp).json()
    assert old["implementation"].startswith("PL/SQL")
    assert [p["project_id"] for p in old["projects"]] == [p["project_id"] for p in new]
    assert [p["status_label"] for p in old["projects"]] == [p["status_label"] for p in new]
    assert client.get("/v1/legacy/district-dashboard/MVS", headers=mvp).status_code == 403


# --- strangler-fig migration switch -----------------------------------------


def test_migration_state_lists_every_legacy_page(client, mvp):
    s = client.get("/v1/migration", headers=mvp).json()
    assert s["apex_app_id"] == 100
    assert s["apex_base_url"].endswith("/ords")
    assert [r["route_key"] for r in s["routes"]] == ["enterprise", "org", "project", "ops"]
    assert s["total_count"] == 4
    for r in s["routes"]:
        assert r["implementation"] in ("APEX", "REACT")
        assert r["apex_url"] == f"{s['apex_base_url']}/f?p=100:{r['apex_page_id']}"
        assert r["api_routes"]


def test_migration_flip_is_hq_only(client, mvp, mvd):
    for h in (mvp, mvd):
        assert client.put("/v1/migration/ops", json={"implementation": "REACT"}, headers=h).status_code == 403


def test_migration_flip_and_rollback(client, hq):
    before = client.get("/v1/migration/ops", headers=hq).json()["implementation"]
    try:
        r = client.put("/v1/migration/ops", json={"implementation": "REACT"}, headers=hq).json()
        assert r["implementation"] == "REACT" and r["migrated_at"] is not None
        assert client.get("/v1/migration", headers=hq).json()["migrated_count"] >= 1
        r = client.put("/v1/migration/ops", json={"implementation": "APEX"}, headers=hq).json()
        assert r["implementation"] == "APEX" and r["migrated_at"] is None
    finally:
        client.put("/v1/migration/ops", json={"implementation": before}, headers=hq)


def test_migration_validation(client, hq):
    assert client.put("/v1/migration/ops", json={"implementation": "COBOL"}, headers=hq).status_code == 422
    assert client.put("/v1/migration/nope", json={"implementation": "REACT"}, headers=hq).status_code == 404
    assert client.get("/v1/migration/nope", headers=hq).status_code == 404
