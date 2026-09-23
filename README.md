# USACE EMT — Oracle APEX → FastAPI + React modernization demo

A working demonstration of moving an Oracle APEX application (modelled on the USACE
Enterprise Management Tool, EMT) to a custom FastAPI + React stack **without moving off
Oracle** — page by page, with the real APEX app still running while each page flips.
Everything runs locally on Oracle Database 23ai Free + APEX 24.2 + ORDS and is populated from
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
make up            # oracle (+APEX) + ords + api + web; api loads fixtures on first start
```

* Web (the "after" shell): <http://localhost:5173> — sign in as any dev persona (password `demo`)
* Legacy APEX app (the "before"): <http://localhost:8080/ords/f?p=100> — APEX Builder at
  <http://localhost:8080/ords/apex> (workspace `EMT`, user `EMT_DEV`, password `Apex_Passw0rd!1`)
* API: <http://localhost:8000/docs> (OpenAPI), <http://localhost:8000/health>

**First boot takes ~8–10 minutes**: Oracle Free initialises, downloads and installs APEX 24.2
(~300 MB, cached in the `oracle-data` volume), applies `db/migrations`, creates the `EMT`
workspace and imports `db/apex/f100.sql`. Only then does the health check pass and ORDS/API
start. Subsequent starts take ~1 minute.

### Local development (hot reload)

Requires [uv](https://docs.astral.sh/uv/) and Node 22.

```bash
make oracle                     # Oracle Free + APEX in Docker, waits for healthy (slow first time)
cd api && uv sync && cd ..
cd web && npm install && cd ..  # postinstall copies USWDS fonts/images into web/public/uswds
make load                       # migrations + fixture loaders (idempotent)
make api                        # http://localhost:8000  (terminal 1)
make web                        # http://localhost:5173  (terminal 2, proxies /api → :8000)
make test                       # 32 integration tests against the live Oracle
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

## The legacy APEX application (the "before")

`db/apex/f100.sql` is a real Oracle APEX 24.2 export (application 100, *Enterprise Management
Tool (EMT)*), imported into workspace `EMT` on the same `emt` schema the API uses:

| Page | Name | Built from |
|---|---|---|
| 1 | Dashboard | four JET chart regions over `v_emt_division_rollup`, `v_emt_hazard_mix`, `v_emt_obligations_by_period` |
| 2 | Districts | interactive report over `v_emt_org_rollup` (org picked by an IR row filter in the URL) |
| 3 | Projects | interactive report over `v_emt_projects`, name links to page 5 |
| 4 | Lock Operations | interactive report over `v_emt_lock_status` (LPMS) |
| 5 | Project Detail | page items filled by a `BEFORE_HEADER` PL/SQL page process calling `emt_legacy.project_status_label`; *Recalculate status* button re-runs it; classic report over `contracts` |

Pages 1–5 are public (no APEX login) and allow framing, so the React shell can embed them.
USACE already runs public APEX/ORDS apps of exactly this shape — Corps Locks
(<https://ndc.ops.usace.army.mil/ords/f?p=108>) is the source of the LPMS fixture.

## The strangler-fig switch

```
  React shell  ──►  GET /v1/migration  ──►  migration_routes (Oracle)
                                               route_key │ apex_page_id │ implementation
                                               enterprise│      1       │ APEX  ─► <iframe ords/f?p=100:1>
                                               org       │      2       │ APEX
                                               project   │      5       │ REACT ─► <ProjectPage/> + /v1/projects/{id}
                                               ops       │      4       │ APEX
```

Every legacy page has a row in `migration_routes`. When a row says `APEX`, the shell embeds
the ORDS-served APEX page (users keep the legacy UI, session state and PL/SQL processes for
that page only). When it says `REACT`, the shell renders the rewritten page from `/v1/*`.
`PUT /v1/migration/{route}` (HQ only) is the only write; flipping back is the same UPDATE.
Both tiers read the same tables, so nothing about the data changes when a page moves.

## Demo script (≈10 minutes)

1. **Start on the old app.** Open <http://localhost:8080/ords/f?p=100> — the APEX EMT:
   Dashboard, Districts, Projects → Project Detail (PL/SQL page process), Lock Operations.
2. **Same app inside the new shell.** Sign in to <http://localhost:5173> as `hq.analyst`.
   Every page is still the embedded APEX page (red *LEGACY · Oracle APEX* pill).
3. **Migrate one page.** Click *Migrate to React →* on the Enterprise page: the APEX
   dashboard is replaced by the React/USWDS dashboard served from `/v1/portfolio`, same
   numbers. *Side by side* shows both against the same Oracle tables. Roll it back — APEX
   is live again instantly.
4. **Migration control** page: one row per legacy page, who owns it today, what changed.
   Flip Drill-down and Project detail; open a project — the React page replaces the APEX
   PL/SQL page process with `services.py`, and the PL/SQL coexistence page proves the two
   agree row for row (`test_legacy_dashboard_matches_new_route`).
5. **Scoping**: switch to `mvp.pm`; portfolio shrinks to St. Paul, `/orgs/MVS` is 403, and
   the migration buttons disappear (HQ-only, enforced by the API, not the UI).
6. **Data lineage**: every row carries a `source_load_id`; the Sources page shows fetch
   time, URL and row count per public source.
7. **Oracle didn't move**: `docker compose exec oracle sqlplus emt/emt_Passw0rd@FREEPDB1`
   — same tables, same package, APEX Builder still opens the legacy app.

## Layout

```
data/       fetch.py refreshes public fixtures; fixtures/ (committed) ; reference/orgs.csv
db/         migrations/V001 canonical schema, V002 emt_legacy PL/SQL package, V003 migration_routes,
            V004 v_emt_* views the APEX app reads
            apex/f100.sql — APEX 24.2 export of the legacy EMT app (application 100)
            oracle/startup/ — first-boot init (emt_init.sh + steps/): app user, APEX install, migrations, workspace + import
            legacy/apex_page_process_example.sql — annotated district-dashboard page process (shown on the coexistence page)
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
| `GET /v1/migration[/{route}]`, `PUT /v1/migration/{route}` (HQ) | which tier owns each legacy APEX page; flip / roll back |
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
passwords (Oracle, APEX, ORDS) and the JWT secret in `docker-compose.yml` are local-development defaults only.
