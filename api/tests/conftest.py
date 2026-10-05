"""Integration tests run against a real Oracle (docker compose up oracle). Skipped when it is unreachable."""

import os

import oracledb
import pytest
from fastapi.testclient import TestClient

from app import config


def _oracle_reachable() -> bool:
    try:
        with oracledb.connect(user=config.ORACLE_USER, password=config.ORACLE_PASSWORD, dsn=config.ORACLE_DSN):
            return True
    except oracledb.Error:
        return False


@pytest.fixture(scope="session")
def client():
    if not _oracle_reachable():
        pytest.skip(f"Oracle not reachable at {config.ORACLE_DSN}")
    os.environ.setdefault("LOAD_FIXTURES_ON_START", "1")
    config.LOAD_FIXTURES_ON_START = True
    from app.main import app

    with TestClient(app) as c:
        yield c


def _token(client: TestClient, username: str) -> dict[str, str]:
    r = client.post("/auth/token", json={"username": username, "password": "demo"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def hq(client):
    return _token(client, "hq.analyst")


@pytest.fixture(scope="session")
def mvd(client):
    return _token(client, "mvd.chief")


@pytest.fixture(scope="session")
def mvp(client):
    return _token(client, "mvp.pm")
