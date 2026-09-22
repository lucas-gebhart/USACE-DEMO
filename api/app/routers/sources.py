from fastapi import APIRouter, Depends

from app import services
from app.auth import User, current_user
from app.models import SourceLoad

router = APIRouter(prefix="/v1/sources", tags=["lineage"])


@router.get("", response_model=list[SourceLoad], summary="Latest load per public source: URL, fetch date, row counts")
def list_sources(user: User = Depends(current_user)) -> list[SourceLoad]:
    return services.sources()
