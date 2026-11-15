from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user, get_rag_service
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.schemas.auth import ErrorResponse
from app.schemas.knowledge import RagQuery, RagResponse
from app.services.knowledge_service import RagService
from app.utils.network import get_client_ip

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=RagResponse, responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
             dependencies=[Depends(rate_limit("ai", "ai_rate_limit_attempts", "ai_rate_limit_window_seconds"))])
def query_documents(payload: RagQuery, request: Request, user: User = Depends(get_current_user),
                    service: RagService = Depends(get_rag_service)) -> RagResponse:
    """Answer from the user's own documents with verified citations. Works without an LLM (excerpts only)."""
    return service.query(user, payload.question, payload.document_ids, get_client_ip(request))
