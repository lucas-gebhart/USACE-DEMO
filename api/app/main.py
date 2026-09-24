import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config, db
from app.auth import visible_orgs
from app.routers import (
    assets,
    auth,
    contracts,
    legacy,
    migration,
    ops,
    orgs,
    portfolio,
    projects,
    sources,
    workforce,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

DESCRIPTION = """
Custom-code replacement for an Oracle APEX dashboard tier. Oracle stays the system of
record; page logic moves into versioned Python routes with typed responses.

All data is **public**: USAspending (agency 096 + Army district awards), FY2025 Civil Works
O&M justification sheets, the National Inventory of Dams, and the Corps Locks / NTNI ORDS
feeds. None of it is CEFMS, EMS, P2/CMP, or BUILDER; each is a proxy for that domain.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_pool()
    if config.LOAD_FIXTURES_ON_START:
        from loaders import migrate_and_load

        with db.connection() as conn:
            migrate_and_load(conn)
        visible_orgs.cache_clear()
    yield
    db.close_pool()


app = FastAPI(
    title="EMT Modernization API (Oracle APEX -> FastAPI)",
    version="0.1.0",
    description=DESCRIPTION,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"], allow_credentials=True
)

for r in (auth, portfolio, orgs, projects, contracts, assets, ops, workforce, legacy, migration, sources):
    app.include_router(r.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    row = db.query_one("SELECT SYS_CONTEXT('USERENV', 'DB_NAME') AS db, SYSTIMESTAMP AS at FROM dual")
    return {"status": "ok", "database": row["db"], "db_time": row["at"].isoformat()}
