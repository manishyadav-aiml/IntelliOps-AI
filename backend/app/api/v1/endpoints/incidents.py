from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import get_current_user, get_incident_service, get_investigation_service
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.schemas.auth import ErrorResponse
from app.schemas.incident import (
    EventRead,
    IncidentCreate,
    IncidentDetail,
    IncidentRead,
    IncidentUpdate,
    InvestigateRequest,
    InvestigationRead,
    NoteCreate,
    NoteRead,
    SimilarRead,
)
from app.schemas.log import Page
from app.services.incident_service import IncidentService
from app.services.investigation_service import InvestigationService
from app.utils.network import get_client_ip

router = APIRouter(prefix="/incidents", tags=["incidents"])
_errors = {401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
_ai_limit = rate_limit("ai", "ai_rate_limit_attempts", "ai_rate_limit_window_seconds")


@router.get("", response_model=Page[IncidentRead], responses={401: {"model": ErrorResponse}})
def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Literal["OPEN", "INVESTIGATING", "MITIGATED", "RESOLVED"] | None = Query(None, alias="status"),
    severity: Literal["P1", "P2", "P3", "P4"] | None = None,
    service_name: str | None = Query(None, alias="service", max_length=128),
    q: str | None = Query(None, max_length=100),
    sort_by: Literal["created_at", "detection_time", "severity", "status"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    user: User = Depends(get_current_user),
    service: IncidentService = Depends(get_incident_service),
) -> Page[IncidentRead]:
    return service.list_incidents(user, page, page_size, status_filter, severity, service_name, q, sort_by, order == "desc")


@router.post("", response_model=IncidentDetail, status_code=status.HTTP_201_CREATED, responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def create_incident(
    payload: IncidentCreate, request: Request, user: User = Depends(get_current_user),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentDetail:
    incident = service.create_manual(user, payload, get_client_ip(request))
    return service.detail(user, incident.id)


@router.get("/{incident_id}", response_model=IncidentDetail, responses=_errors)
def get_incident(incident_id: int, user: User = Depends(get_current_user), service: IncidentService = Depends(get_incident_service)) -> IncidentDetail:
    return service.detail(user, incident_id)


@router.patch("/{incident_id}", response_model=IncidentDetail, responses={**_errors, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def update_incident(
    incident_id: int, payload: IncidentUpdate, request: Request, user: User = Depends(get_current_user),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentDetail:
    service.update(user, incident_id, payload, get_client_ip(request))
    return service.detail(user, incident_id)


@router.get("/{incident_id}/timeline", response_model=list[EventRead], responses=_errors)
def get_timeline(
    incident_id: int,
    event_type: list[str] | None = Query(None, max_length=20),
    start: datetime | None = None,
    end: datetime | None = None,
    user: User = Depends(get_current_user),
    service: IncidentService = Depends(get_incident_service),
) -> list[EventRead]:
    return service.timeline(user, incident_id, event_type, start, end)


@router.get("/{incident_id}/similar", response_model=list[SimilarRead], responses=_errors)
def get_similar(incident_id: int, user: User = Depends(get_current_user), service: IncidentService = Depends(get_incident_service)) -> list[SimilarRead]:
    return service.similar(user, incident_id)


@router.post("/{incident_id}/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED, responses=_errors)
def add_note(
    incident_id: int, payload: NoteCreate, request: Request, user: User = Depends(get_current_user),
    service: IncidentService = Depends(get_incident_service),
) -> NoteRead:
    note = service.add_note(user, incident_id, payload.content, get_client_ip(request))
    return NoteRead(id=note.id, author_id=note.author_id, author_name=user.full_name, content=note.content, created_at=note.created_at)


@router.post(
    "/{incident_id}/investigate",
    response_model=InvestigationRead,
    responses={**_errors, 429: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    dependencies=[Depends(_ai_limit)],
)
def investigate_incident(
    incident_id: int, request: Request, payload: InvestigateRequest | None = None,
    user: User = Depends(get_current_user), service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationRead:
    """AI suggestions only. Returns 503 (code llm_*) if the AI service is unavailable; everything else still works."""
    record = service.investigate(user, incident_id, payload.question if payload else None, get_client_ip(request))
    return InvestigationRead.model_validate(record)
