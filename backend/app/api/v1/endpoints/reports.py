import re

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_user, get_report_service
from app.models.user import User
from app.schemas.auth import ErrorResponse
from app.schemas.knowledge import ReportGenerate, ReportRead
from app.schemas.log import Page
from app.services.report_service import MEDIA_TYPES, ReportService
from app.utils.network import get_client_ip

router = APIRouter(prefix="/reports", tags=["reports"])
_errors = {401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}


@router.get("", response_model=Page[ReportRead], responses={401: {"model": ErrorResponse}})
def list_reports(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                 user: User = Depends(get_current_user), service: ReportService = Depends(get_report_service)) -> Page[ReportRead]:
    return service.list_reports(user, page, page_size)


@router.post("/generate", response_model=ReportRead, status_code=status.HTTP_201_CREATED, responses=_errors)
def generate_report(payload: ReportGenerate, request: Request, user: User = Depends(get_current_user),
                    service: ReportService = Depends(get_report_service)) -> ReportRead:
    return ReportRead.model_validate(service.generate(user, payload.incident_id, payload.format, get_client_ip(request)))


@router.get("/{report_id}/download", responses=_errors)
def download_report(report_id: int, user: User = Depends(get_current_user), service: ReportService = Depends(get_report_service)) -> FileResponse:
    report, path = service.file_for_download(user, report_id)
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", report.filename)
    return FileResponse(path, media_type=MEDIA_TYPES[report.format], filename=safe_name)
