from fastapi import APIRouter, Depends

from app.auth import DEV_USERS, TokenRequest, TokenResponse, User, authenticate, current_user, issue_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/users", summary="Dev-IdP personas (stand-in for CAC / EAMS-A directory)")
def list_dev_users() -> list[dict]:
    return [u.__dict__ for u in DEV_USERS.values()]


@router.post("/token", response_model=TokenResponse)
def token(req: TokenRequest) -> TokenResponse:
    return issue_token(authenticate(req))


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return user.__dict__
