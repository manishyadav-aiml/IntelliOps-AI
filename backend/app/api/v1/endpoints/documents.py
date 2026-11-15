from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Request, Response, UploadFile, status

from app.api.deps import get_current_user, get_document_processor, get_document_service
from app.core.config import Settings, get_settings
from app.models.user import User
from app.schemas.auth import ErrorResponse
from app.schemas.knowledge import DocumentRead
from app.schemas.log import Page
from app.services.document_upload import save_document
from app.services.knowledge_service import DocumentProcessor, DocumentService
from app.utils.network import get_client_ip

router = APIRouter(prefix="/documents", tags=["documents"])
_errors = {401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED,
             responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 401: {"model": ErrorResponse}})
async def upload_document(
    request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...),
    user: User = Depends(get_current_user), service: DocumentService = Depends(get_document_service),
    processor: DocumentProcessor = Depends(get_document_processor), settings: Settings = Depends(get_settings),
) -> DocumentRead:
    """Validate and store the document, then extract/chunk/embed/index it in the background."""
    stored, size, name = await save_document(file, service.user_directory(user), settings.max_upload_bytes)
    doc = service.register(user, stored, size, name, get_client_ip(request))
    background_tasks.add_task(processor.process, doc.id)
    return DocumentRead.model_validate(doc)


@router.get("", response_model=Page[DocumentRead], responses={401: {"model": ErrorResponse}})
def list_documents(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status", pattern="^(PENDING|PROCESSING|COMPLETED|FAILED)$"),
    q: str | None = Query(None, max_length=100),
    user: User = Depends(get_current_user), service: DocumentService = Depends(get_document_service),
) -> Page[DocumentRead]:
    return service.list_documents(user, page, page_size, status_filter, q)


@router.get("/{document_id}", response_model=DocumentRead, responses=_errors)
def get_document(document_id: int, user: User = Depends(get_current_user), service: DocumentService = Depends(get_document_service)) -> DocumentRead:
    return DocumentRead.model_validate(service.get(user, document_id))


@router.post("/{document_id}/index", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED,
             responses={**_errors, 409: {"model": ErrorResponse}})
def reindex_document(
    document_id: int, request: Request, background_tasks: BackgroundTasks, user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service), processor: DocumentProcessor = Depends(get_document_processor),
) -> DocumentRead:
    doc = service.request_index(user, document_id, get_client_ip(request))
    background_tasks.add_task(processor.process, doc.id)
    return DocumentRead.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, responses={**_errors, 409: {"model": ErrorResponse}})
def delete_document(
    document_id: int, request: Request, user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> Response:
    service.delete(user, document_id, get_client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
