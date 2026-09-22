# USACE EMT — Oracle APEX → FastAPI + React modernization demo

A working demonstration of moving an Oracle APEX application (modelled on the USACE
Enterprise Management Tool, EMT) to a custom FastAPI + React stack **without moving off
Oracle**. Everything runs locally on Oracle Database 23ai Free and is populated from
public USACE / Treasury data. Nothing here is CEFMS, EMS, P2/CMP or BUILDER data — every
source is a labelled public proxy (see [Data sources](#data-sources-all-public-proxies)).

```
  BEFORE — APEX owns the whole stack           AFTER — strangler fig, Oracle stays put

  ┌──────────────────────────────┐             ┌──────────────┐    ┌──────────────────┐
  │ Oracle APEX                  │             │ React + USWDS│───▶│ FastAPI  /v1/*   │
  │  pages · session state       │             │ (web/)       │    │ JWT roles, tests │
  │  interactive reports         │             └──────────────┘    │ OpenAPI (api/)   │
  │  PL/SQL page processes       │                                 └────────┬─────────┘
  └──────────────┬───────────────┘                  APEX/ORDS (legacy      │ SQL +
                 │ SQL                               pages, still served)   │ SYS_REFCURSOR
  ┌──────────────▼───────────────┐             ┌────────────┴──────────────▼───────────┐
  │ Oracle DB                    │             │ Oracle DB 23ai — unchanged tables,     │
  │  tables + PL/SQL packages    │             │  emt_legacy PL/SQL package retained    │
  └──────────────────────────────┘             └────────────────────────────────────────┘
```

## Quick start

Prerequisites: Docker (with Compose), ~8 GB free RAM for Oracle Free.

```bash
git clone https://github.com/lucas-gebhart/USACE-DEMO && cd USACE-DEMO
make up            # oracle + api + web; api migrates and loads fixtures on first start
```

* Web: <http://localhost:5173> — sign in as any dev persona (password `demo`)
* API: <http://localhost:8000/docs> (OpenAPI), <http://localhost:8000/health>

First boot takes ~1–2 minutes while Oracle initialises; the API waits on its health check.

### Local development (hot reload)

Requires [uv](https://docs.astral.sh/uv/) and Node 22.

```bash
make oracle                     # Oracle Free in Docker, waits for healthy
cd api && uv sync && cd ..
cd web && npm install && cd ..  # postinstall copies USWDS fonts/images into web/public/uswds
make load                       # migrations + fixture loaders (idempotent)
make api                        # http://localhost:8000  (terminal 1)
make web                        # http://localhost:5173  (terminal 2, proxies /api → :8000)
make test                       # 28 integration tests against the live Oracle
make lint                       # ruff + eslint + tsc
```

## Dev personas and scoping

Roles and org scope come from JWT claims (stand-ins for CAC / EAMS-A / OIDC claims in
production). Scope is resolved from the `organizations` hierarchy in Oracle
(`START WITH … CONNECT BY`); out-of-scope orgs return `403`.

| Username     | Role     | Org | Sees                              |
|--------------|----------|-----|-----------------------------------|
| `hq.analyst` | HQ       | HQ  | Everything                        |
| `mvd.chief`  | DIVISION | MVD | Mississippi Valley Division + districts |
| `lrd.chief`  | DIVISION | LRD | Great Lakes & Ohio River Division + districts |
| `mvp.pm`     | DISTRICT | MVP | St. Paul District only            |

## Demo script (≈10 minutes)

1. **The "before" is real.** USACE already runs public Oracle APEX/ORDS apps — open
   Corps Locks (<https://ndc.ops.usace.army.mil/ords/f?p=108>). The demo's
   Operations page renders the same LPMS feed from a typed FastAPI route.
2. **Enterprise view** (`hq.analyst`): FY25 O&M projects, USAspending execution,
   NID hazard/condition, roll-up by division/district from Oracle view `v_org_rollup`.
3. **Drill down**: MVD → MVP → a project. Status labels (`GROWING/SHRINKING/STEADY`)
   are computed by the *same rule* in PL/SQL and Python.
4. **Scoping**: switch to `mvp.pm`; portfolio shrinks to St. Paul, `/orgs/MVS` is 403.
5. **APEX coexistence page**: an APEX page process
   (`db/legacy/apex_page_process_example.sql`) beside the FastAPI route
   (`api/app/routers/orgs.py`). The live table calls the retained PL/SQL package
   through `SYS_REFCURSOR` *and* the rewritten route, row for row — the test suite
   asserts they agree (`api/tests/test_api.py::test_legacy_dashboard_matches_new_route`).
6. **Data lineage**: every row carries a `source_load_id`; the Sources page shows fetch
   time, URL and row count per public source.
7. **Oracle didn't move**: `docker compose exec oracle sqlplus emt/emt_Passw0rd@FREEPDB1`
   — same tables, same package, new consumers.

## Layout

```
data/       fetch.py refreshes public fixtures; fixtures/ (committed) ; reference/orgs.csv
db/         migrations/V001 canonical schema + v_org_rollup, V002 emt_legacy PL/SQL package
            legacy/apex_page_process_example.sql — the APEX "before"
api/        FastAPI (app/), loaders (python -m loaders), pytest integration suite (tests/)
web/        React 19 + USWDS 3 + TanStack Query + Recharts; nginx image proxies /api
docs/       demo plan (interactive HTML)
```

### API surface

| Route | Purpose |
|---|---|
| `POST /auth/token`, `GET /auth/me`, `GET /auth/users` | dev IdP: personas → JWT |
| `GET /v1/portfolio` | scoped enterprise roll-up, budget years, business-line & hazard mix |
| `GET /v1/orgs`, `GET /v1/orgs/{code}` | hierarchy + district dashboard (APEX page-process replacement) |
| `GET /v1/projects[/{id}[/related]]` | FY25 O&M projects, business lines, heuristic related awards/dams |
| `GET /v1/contracts` | USAspending awards by district DoDAAC prefix |
| `GET /v1/assets` | NID dams (hazard, condition, inspection) |
| `GET /v1/ops/locks`, `/rivers`, `/notices` | LPMS lock status, NTNI navigation notices |
| `GET /v1/workforce` | personnel object-class obligations (EMS proxy) |
| `GET /v1/legacy/district-dashboard/{code}`, `/status-label` | calls `emt_legacy` PL/SQL directly |
| `GET /v1/sources` | source-load lineage |

## Data sources (all public proxies)

| EMT data area (internal system) | Public proxy used | Not shown |
|---|---|---|
| Financial & execution (CEFMS) | [USAspending](https://api.usaspending.gov/docs/endpoints) agency 096 budgetary resources/obligations; Army awards by district DoDAAC (`W912xx`) | CEFMS obligation/disbursement detail |
| Workforce (EMS labor logs) | USAspending personnel object classes; [OPM FedScope](https://data.opm.gov/get-data/data-downloads) (offline) | Labor hours, project charging |
| Scheduling & lifecycle (P2 / CMP) | [FY2025 Civil Works O&M justification sheets](https://www.usace.army.mil/missions/civil-works/budget/) | Schedules, milestones, CMP records |
| Infrastructure status (BUILDER SMS) | [National Inventory of Dams](https://nid.sec.usace.army.mil/) | Facility condition indices, work items |
| Operations | [Corps Locks / LPMS](https://ndc.ops.usace.army.mil/ords/f?p=108) and NTNI ORDS JSON | — (these are the real public APEX apps) |

`python3 data/fetch.py` (needs `pdftotext` from poppler-utils) re-pulls everything and records URL, fetch time and row counts in
each fixture's `_meta.json`; loaders write those into `source_loads`.

## Non-goals

Not a production EMT replacement; no access to USACE internal systems or credentials;
passwords and JWT secret in `docker-compose.yml` are local-development defaults only.
