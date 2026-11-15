from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Request, Response, UploadFile, status

from app.api.deps import get_anomaly_service, get_current_user, get_log_processor, get_log_service
from app.core.config import Settings, get_settings
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.schemas.auth import ErrorResponse
from app.schemas.incident import AnalysisResult
from app.schemas.log import (
    FacetsRead,
    LogEntryRead,
    LogUploadRead,
    Page,
    TemplateSummary,
    UploadStatus,
)
from app.services.anomaly_service import AnomalyService
from app.services.log_processing import LogProcessor
from app.services.log_service import LogService
from app.services.log_upload import save_upload
from app.utils.network import get_client_ip

router = APIRouter(prefix="/logs", tags=["logs"])
_upload_limit = rate_limit("upload", "upload_rate_limit_attempts", "upload_rate_limit_window_seconds")
_errors = {401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}


@router.post(
    "/upload",
    response_model=LogUploadRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
    dependencies=[Depends(_upload_limit)],
)
async def upload_log(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    service: LogService = Depends(get_log_service),
    processor: LogProcessor = Depends(get_log_processor),
    settings: Settings = Depends(get_settings),
) -> LogUploadRead:
    """Validate and store the file, then parse it in the background (poll GET /logs/{id})."""
    stored, size, display_name = await save_upload(
        file, service.user_directory(user), settings.max_upload_bytes
    )
    upload = service.register_upload(user, stored, size, display_name, get_client_ip(request))
    background_tasks.add_task(processor.process, upload.id)
    return LogUploadRead.model_validate(upload)


@router.get("", response_model=Page[LogUploadRead], responses=_errors)
def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: UploadStatus | None = Query(None, alias="status"),
    q: str | None = Query(None, max_length=100),
    sort_by: Literal["created_at", "filename", "size_bytes"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    user: User = Depends(get_current_user),
    service: LogService = Depends(get_log_service),
) -> Page[LogUploadRead]:
    return service.list_uploads(user, page, page_size, status_filter, q, sort_by, order == "desc")


@router.get("/{log_id}", response_model=LogUploadRead, responses=_errors)
def get_log(
    log_id: int, user: User = Depends(get_current_user), service: LogService = Depends(get_log_service)
) -> LogUploadRead:
    return LogUploadRead.model_validate(service.get_upload(user, log_id))


@router.get("/{log_id}/entries", response_model=Page[LogEntryRead], responses=_errors)
def list_log_entries(
    log_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    level: str | None = Query(None, max_length=16),
    service_name: str | None = Query(None, alias="service", max_length=128),
    template_id: int | None = None,
    q: str | None = Query(None, max_length=200),
    start: datetime | None = None,
    end: datetime | None = None,
    sort_by: Literal["line_number", "timestamp", "level"] = "line_number",
    order: Literal["asc", "desc"] = "asc",
    user: User = Depends(get_current_user),
    service: LogService = Depends(get_log_service),
) -> Page[LogEntryRead]:
    return service.list_entries(
        user, log_id, page, page_size, level, service_name, template_id, q, start, end, sort_by, order == "desc"
    )


@router.get("/{log_id}/entries/{entry_id}", response_model=LogEntryRead, responses=_errors)
def get_log_entry(
    log_id: int,
    entry_id: int,
    user: User = Depends(get_current_user),
    service: LogService = Depends(get_log_service),
) -> LogEntryRead:
    entry = service.get_entry(user, log_id, entry_id)
    item = LogEntryRead.model_validate(entry)
    item.source_file = service.get_upload(user, log_id).filename
    return item


@router.get("/{log_id}/templates", response_model=list[TemplateSummary], responses=_errors)
def list_log_templates(
    log_id: int,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: LogService = Depends(get_log_service),
) -> list[TemplateSummary]:
    return service.templates(user, log_id, limit)


@router.get("/{log_id}/facets", response_model=FacetsRead, responses=_errors)
def get_log_facets(
    log_id: int, user: User = Depends(get_current_user), service: LogService = Depends(get_log_service)
) -> FacetsRead:
    return service.facets(user, log_id)


@router.post(
    "/{log_id}/reprocess",
    response_model=LogUploadRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses={**_errors, 409: {"model": ErrorResponse}},
)
def reprocess_log(
    log_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    service: LogService = Depends(get_log_service),
    processor: LogProcessor = Depends(get_log_processor),
) -> LogUploadRead:
    """Retry PARSING of a FAILED upload."""
    upload = service.request_reprocess(user, log_id, get_client_ip(request))
    background_tasks.add_task(processor.process, upload.id)
    return LogUploadRead.model_validate(upload)


@router.post(
    "/{log_id}/analyze",
    response_model=AnalysisResult,
    responses={**_errors, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def analyze_log(
    log_id: int,
    request: Request,
    window_seconds: int | None = Query(None, ge=10, le=3600, description="Aggregation window (default from settings)"),
    user: User = Depends(get_current_user),
    anomalies: AnomalyService = Depends(get_anomaly_service),
) -> AnalysisResult:
    """Run anomaly detection on a parsed log file; anomalous windows are grouped into incidents.

    Idempotent: re-running replaces this file's detections and never duplicates incidents.
    """
    return anomalies.run(user, log_id, window_seconds, get_client_ip(request))


@router.delete(
    "/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**_errors, 409: {"model": ErrorResponse}},
)
def delete_log(
    log_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    service: LogService = Depends(get_log_service),
) -> Response:
    service.delete_upload(user, log_id, get_client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
