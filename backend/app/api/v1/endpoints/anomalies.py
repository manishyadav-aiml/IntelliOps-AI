from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_anomaly_service, get_current_user
from app.models.user import User
from app.schemas.auth import ErrorResponse
from app.schemas.incident import AnomalyRead
from app.schemas.log import Page
from app.services.anomaly_service import AnomalyService

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("", response_model=Page[AnomalyRead], responses={401: {"model": ErrorResponse}})
def list_anomalies(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    upload_id: int | None = None,
    detected_only: bool = False,
    sort_by: Literal["window_start", "anomaly_score"] = "window_start",
    order: Literal["asc", "desc"] = "desc",
    user: User = Depends(get_current_user),
    service: AnomalyService = Depends(get_anomaly_service),
) -> Page[AnomalyRead]:
    return service.list_anomalies(user, page, page_size, upload_id, detected_only, sort_by, order == "desc")


@router.get("/{anomaly_id}", response_model=AnomalyRead, responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def get_anomaly(
    anomaly_id: int, user: User = Depends(get_current_user), service: AnomalyService = Depends(get_anomaly_service)
) -> AnomalyRead:
    return AnomalyRead.model_validate(service.get_anomaly(user, anomaly_id))
