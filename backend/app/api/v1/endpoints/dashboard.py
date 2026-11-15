from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_dashboard_service
from app.models.user import User
from app.schemas.auth import ErrorResponse
from app.schemas.knowledge import DashboardSummary, DashboardTrends, NamedCount
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
_401 = {401: {"model": ErrorResponse}}


@router.get("/summary", response_model=DashboardSummary, responses=_401)
def summary(start: datetime | None = None, end: datetime | None = None, service: str | None = Query(None, max_length=128),
            user: User = Depends(get_current_user), svc: DashboardService = Depends(get_dashboard_service)) -> DashboardSummary:
    return svc.summary(user, start, end, service)


@router.get("/trends", response_model=DashboardTrends, responses=_401)
def trends(bucket: Literal["hour", "day"] = "hour", start: datetime | None = None, end: datetime | None = None,
           service: str | None = Query(None, max_length=128), user: User = Depends(get_current_user),
           svc: DashboardService = Depends(get_dashboard_service)) -> DashboardTrends:
    return svc.trends(user, bucket, start, end, service)


@router.get("/services", response_model=list[NamedCount], responses=_401)
def services(user: User = Depends(get_current_user), svc: DashboardService = Depends(get_dashboard_service)) -> list[NamedCount]:
    return svc.services(user)
