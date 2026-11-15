"""Password hashing (bcrypt) and JWT helpers (PyJWT)."""

import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

import bcrypt
import jwt


class InvalidTokenError(Exception):
    """Raised for any token that is malformed, tampered with, expired or missing claims."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


@lru_cache
def dummy_hash() -> str:
    """A valid hash used to equalise timing when a login email does not exist."""
    return hash_password("intelliops-timing-equaliser")


def create_access_token(
    subject: str, secret: str, algorithm: str, expires_minutes: int
) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "iat": now, "exp": expires_at, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, secret, algorithm=algorithm), expires_at


def decode_access_token(token: str, secret: str, algorithm: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token, secret, algorithms=[algorithm], options={"require": ["exp", "iat", "sub"]}
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Invalid or expired token") from exc
