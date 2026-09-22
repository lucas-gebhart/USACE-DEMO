import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


ORACLE_DSN = env("ORACLE_DSN", "localhost:1521/FREEPDB1")
ORACLE_USER = env("ORACLE_USER", "emt")
ORACLE_PASSWORD = env("ORACLE_PASSWORD", "emt_Passw0rd")
JWT_SECRET = env("JWT_SECRET", "dev-only-change-me-not-for-production-0000")
JWT_ISSUER = "emt-demo-dev-idp"
TOKEN_TTL_MINUTES = 8 * 60
DATA_DIR = Path(env("DATA_DIR", str(REPO_ROOT / "data")))
MIGRATIONS_DIR = Path(env("MIGRATIONS_DIR", str(REPO_ROOT / "db" / "migrations")))
LOAD_FIXTURES_ON_START = env("LOAD_FIXTURES_ON_START", "0") == "1"
CORS_ORIGINS = [o for o in env("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o]
