from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import InvalidTokenError, decode_access_token
from app.database.session import get_db, get_session_factory
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.ai.llm_provider import LLMProvider
from app.services.anomaly_service import AnomalyService
from app.services.dashboard_service import DashboardService
from app.services.incident_service import IncidentService
from app.services.investigation_service import InvestigationService
from app.services.knowledge_service import DocumentProcessor, DocumentService, RagService
from app.services.llm_factory import create_provider
from app.services.log_processing import LogProcessor
from app.services.report_service import ReportService
from app.services.log_service import LogService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> AuthService:
    return AuthService(db, settings)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None:
        raise AuthenticationError("Not authenticated")
    try:
        payload = decode_access_token(
            credentials.credentials, settings.jwt_secret, settings.jwt_algorithm
        )
        user_id = int(payload["sub"])
    except (InvalidTokenError, ValueError) as exc:
        raise AuthenticationError("Invalid or expired token") from exc
    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid or expired token")
    return user


def get_log_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> LogService:
    return LogService(db, settings)


def get_processing_session_factory() -> Callable[[], Session]:
    """Background tasks need their own sessions; tests override this dependency."""
    return get_session_factory()


def get_log_processor(
    factory: Callable[[], Session] = Depends(get_processing_session_factory),
    settings: Settings = Depends(get_settings),
) -> LogProcessor:
    return LogProcessor(factory, settings)


def get_llm_provider(settings: Settings = Depends(get_settings)) -> LLMProvider | None:
    """Overridden in tests with a fake provider so no real LLM is ever called."""
    return create_provider(settings)


def get_incident_service(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> IncidentService:
    return IncidentService(db, settings)


def get_anomaly_service(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> AnomalyService:
    return AnomalyService(db, settings)


def get_investigation_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
    provider: LLMProvider | None = Depends(get_llm_provider),
) -> InvestigationService:
    return InvestigationService(db, settings, provider)


def get_document_service(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> DocumentService:
    return DocumentService(db, settings)


def get_document_processor(
    factory: Callable[[], Session] = Depends(get_processing_session_factory),
    settings: Settings = Depends(get_settings),
) -> DocumentProcessor:
    return DocumentProcessor(factory, settings)


def get_rag_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
    provider: LLMProvider | None = Depends(get_llm_provider),
) -> RagService:
    return RagService(db, settings, provider)


def get_report_service(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ReportService:
    return ReportService(db, settings)


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)
