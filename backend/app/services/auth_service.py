from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    dummy_hash,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserCreate


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.users = UserRepository(db)
        self.audit = AuditRepository(db)

    def register(self, data: UserCreate, ip_address: str | None = None) -> User:
        email = normalize_email(data.email)
        if self.users.get_by_email(email):
            raise ConflictError("An account with this email already exists")
        user = User(
            email=email, full_name=data.full_name, hashed_password=hash_password(data.password)
        )
        try:
            self.users.add(user)
            self.audit.record("user.registered", user.id, ip_address, "user", str(user.id))
            self.db.commit()
        except IntegrityError as exc:  # concurrent registration with the same email
            self.db.rollback()
            raise ConflictError("An account with this email already exists") from exc
        return user

    def login(
        self, email: str, password: str, ip_address: str | None = None
    ) -> tuple[User, str, datetime]:
        user = self.users.get_by_email(normalize_email(email))
        # Always run a bcrypt verification so timing does not reveal whether the email exists.
        password_ok = verify_password(password, user.hashed_password if user else dummy_hash())
        if user is None or not password_ok or not user.is_active:
            self.audit.record("auth.login.failed", user.id if user else None, ip_address)
            self.db.commit()
            raise AuthenticationError("Invalid email or password")
        token, expires_at = create_access_token(
            str(user.id),
            self.settings.jwt_secret,
            self.settings.jwt_algorithm,
            self.settings.access_token_expire_minutes,
        )
        self.audit.record("auth.login.success", user.id, ip_address)
        self.db.commit()
        return user, token, expires_at

    def logout(self, user: User, ip_address: str | None = None) -> None:
        """Records the event only. JWTs are stateless and are NOT revoked server-side."""
        self.audit.record("auth.logout", user.id, ip_address)
        self.db.commit()
