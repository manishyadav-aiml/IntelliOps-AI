from pathlib import Path

from fastapi import APIRouter, Depends

from app import __version__
from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.ml.anomaly_detection import load_latest_model
from app.models.user import User
from app.schemas.auth import ErrorResponse
from app.schemas.knowledge import SystemStatus
from app.services.embedder_cache import get_embedder
from app.services.llm_factory import llm_configured

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatus, responses={401: {"model": ErrorResponse}})
def system_status(user: User = Depends(get_current_user), settings: Settings = Depends(get_settings)) -> SystemStatus:
    """Non-secret runtime information for the Settings page. API keys are never returned."""
    embedder = get_embedder(settings)
    model = None
    try:
        loaded = load_latest_model(Path(settings.models_dir))
        model = loaded.version if loaded else None
    except Exception:
        model = None
    try:
        import faiss  # noqa: F401

        backend = "faiss" if settings.matcher == "faiss" else "numpy"
    except ImportError:
        backend = "numpy"
    return SystemStatus(
        version=__version__, environment=settings.app_env, llm_provider=settings.llm_provider,
        llm_configured=llm_configured(settings), embedder=embedder.name,
        embedder_fallback_reason=embedder.fallback_reason, vector_backend=backend,
        template_miner=settings.log_template_miner, trained_model=model,
    )
