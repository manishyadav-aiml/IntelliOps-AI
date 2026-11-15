from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        action: str,
        user_id: int | None = None,
        ip_address: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            user_id=user_id,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
        self.db.add(entry)
        return entry
