from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import get_auth_service, get_current_user
from app.core.config import Settings, get_settings
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.schemas.auth import ErrorResponse, LoginRequest, TokenResponse, UserCreate, UserRead
from app.services.auth_service import AuthService
from app.utils.network import get_client_ip

router = APIRouter(prefix="/auth", tags=["auth"])

_register_limit = rate_limit(
    "register", "register_rate_limit_attempts", "register_rate_limit_window_seconds"
)
_login_limit = rate_limit("login", "login_rate_limit_attempts", "login_rate_limit_window_seconds")


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
    dependencies=[Depends(_register_limit)],
)
def register(
    payload: UserCreate, request: Request, service: AuthService = Depends(get_auth_service)
) -> User:
    return service.register(payload, get_client_ip(request))


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
    dependencies=[Depends(_login_limit)],
)
def login(
    payload: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user, token, _ = service.login(payload.email, payload.password, get_client_ip(request))
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead, responses={401: {"model": ErrorResponse}})
def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, responses={401: {"model": ErrorResponse}}
)
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> Response:
    service.logout(current_user, get_client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
