"""Dev identity provider standing in for CAC / EAMS-A OIDC.

Tokens are ordinary OIDC-style JWTs (sub, roles, org claims). In a real deployment
the /auth/token route disappears and `current_user` validates tokens from the
enterprise IdP instead; every route's authorization logic stays the same.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app import config, db


@dataclass(frozen=True)
class User:
    username: str
    display_name: str
    role: str  # HQ | DIVISION | DISTRICT
    org_code: str

    def can_see(self, org_code: str) -> bool:
        return org_code in visible_orgs(self.org_code)


DEV_USERS: dict[str, User] = {
    "hq.analyst": User("hq.analyst", "HQ Program Analyst", "HQ", "HQ"),
    "mvd.chief": User("mvd.chief", "MVD Programs Chief", "DIVISION", "MVD"),
    "mvp.pm": User("mvp.pm", "St. Paul District PM", "DISTRICT", "MVP"),
    "lrd.chief": User("lrd.chief", "LRD Programs Chief", "DIVISION", "LRD"),
}
DEV_PASSWORD = "demo"


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


def issue_token(user: User) -> TokenResponse:
    now = datetime.now(UTC)
    claims = {
        "iss": config.JWT_ISSUER,
        "sub": user.username,
        "name": user.display_name,
        "roles": [user.role],
        "org": user.org_code,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=config.TOKEN_TTL_MINUTES)).timestamp()),
    }
    token = jwt.encode(claims, config.JWT_SECRET, algorithm="HS256")
    return TokenResponse(access_token=token, expires_in=config.TOKEN_TTL_MINUTES * 60, user=user.__dict__)


def authenticate(req: TokenRequest) -> User:
    user = DEV_USERS.get(req.username)
    if user is None or req.password != DEV_PASSWORD:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return user


_bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer token required")
    try:
        claims = jwt.decode(creds.credentials, config.JWT_SECRET, algorithms=["HS256"], issuer=config.JWT_ISSUER)
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {e}") from e
    return User(claims["sub"], claims.get("name", claims["sub"]), claims["roles"][0], claims["org"])


@lru_cache(maxsize=128)
def visible_orgs(org_code: str) -> frozenset[str]:
    """The org itself plus every descendant; HQ therefore sees everything."""
    rows = db.query(
        """SELECT code FROM organizations
            START WITH code = :code
          CONNECT BY PRIOR code = parent_code""",
        code=org_code,
    )
    return frozenset(r["code"] for r in rows)


def require_org_access(user: User, org_code: str) -> None:
    if not user.can_see(org_code):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, f"{user.username} ({user.role} {user.org_code}) cannot view {org_code}"
        )
