"""Application errors rendered in one consistent JSON shape: {"error": {"code", "message"}}."""


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.headers = headers or {}


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_failed"

    def __init__(self, message: str = "Could not validate credentials") -> None:
        super().__init__(message, headers={"WWW-Authenticate": "Bearer"})


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, retry_after: int) -> None:
        super().__init__(
            "Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


class ValidationAppError(AppError):
    status_code = 422
    code = "validation_error"


class InvalidStateError(AppError):
    status_code = 409
    code = "invalid_state"


class AIUnavailableError(AppError):
    """Optional AI features failed; the rest of the application keeps working."""

    status_code = 503
    code = "ai_unavailable"

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
