import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import InvalidStateError, NotFoundError
from app.models.log import LogEntry, LogUpload
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.log_repository import LogRepository
from app.schemas.log import FacetsRead, LogEntryRead, LogUploadRead, Page, TemplateSummary

logger = logging.getLogger(__name__)


class LogService:
    """Log-file operations. Every method is scoped to `user`; other users' data looks non-existent."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repo = LogRepository(db)
        self.audit = AuditRepository(db)

    @property
    def upload_root(self) -> Path:
        return Path(self.settings.upload_dir)

    def user_directory(self, user: User) -> Path:
        return self.upload_root / str(user.id)

    def register_upload(
        self, user: User, stored: Path, size: int, display_name: str, ip: str | None
    ) -> LogUpload:
        upload = LogUpload(
            user_id=user.id,
            filename=display_name,
            stored_path=f"{user.id}/{stored.name}",
            extension=stored.suffix.lower(),
            size_bytes=size,
            status="PENDING",
        )
        try:
            self.repo.add_upload(upload)
            self.audit.record("log.uploaded", user.id, ip, "log_upload", str(upload.id))
            self.db.commit()
        except Exception:
            self.db.rollback()
            stored.unlink(missing_ok=True)
            raise
        return upload

    def _get(self, user: User, upload_id: int) -> LogUpload:
        upload = self.repo.get_upload(user.id, upload_id)
        if upload is None:
            raise NotFoundError("Log file not found")
        return upload

    def get_upload(self, user: User, upload_id: int) -> LogUpload:
        return self._get(user, upload_id)

    def list_uploads(
        self, user: User, page: int, page_size: int, status: str | None, q: str | None,
        sort_by: str, descending: bool,
    ) -> Page[LogUploadRead]:
        rows, total = self.repo.list_uploads(user.id, page, page_size, status, q, sort_by, descending)
        return Page(
            items=[LogUploadRead.model_validate(r) for r in rows], total=total, page=page, page_size=page_size
        )

    def list_entries(
        self, user: User, upload_id: int, page: int, page_size: int, level: str | None,
        service: str | None, template_id: int | None, q: str | None, start: datetime | None,
        end: datetime | None, sort_by: str, descending: bool,
    ) -> Page[LogEntryRead]:
        upload = self._get(user, upload_id)
        rows, total = self.repo.list_entries(
            user.id, upload_id, page, page_size, level, service, template_id, q, start, end, sort_by, descending
        )
        items = []
        for entry, template_text in rows:
            item = LogEntryRead.model_validate(entry)
            item.template_text = template_text
            item.source_file = upload.filename
            items.append(item)
        return Page(items=items, total=total, page=page, page_size=page_size)

    def get_entry(self, user: User, upload_id: int, entry_id: int) -> LogEntry:
        self._get(user, upload_id)
        entry = self.db.get(LogEntry, entry_id)
        if entry is None or entry.upload_id != upload_id or entry.user_id != user.id:
            raise NotFoundError("Log entry not found")
        return entry

    def templates(self, user: User, upload_id: int, limit: int) -> list[TemplateSummary]:
        self._get(user, upload_id)
        return [
            TemplateSummary(
                template_id=t.id, template_hash=t.template_hash, template_text=t.template_text, occurrences=c
            )
            for t, c in self.repo.top_templates(user.id, upload_id, limit)
        ]

    def facets(self, user: User, upload_id: int) -> FacetsRead:
        self._get(user, upload_id)
        levels, services = self.repo.facets(user.id, upload_id)
        return FacetsRead(levels=levels, services=services)

    def request_reprocess(self, user: User, upload_id: int, ip: str | None) -> LogUpload:
        """Re-queue PARSING of a FAILED upload (retry). PENDING is accepted as-is (idempotent)."""
        upload = self._get(user, upload_id)
        if upload.status == "FAILED":
            if not self.repo.reset_failed_to_pending(upload.id):
                raise InvalidStateError("The log file is already being re-queued")
            self.audit.record("log.reprocess_requested", user.id, ip, "log_upload", str(upload.id))
            self.db.commit()
            self.db.refresh(upload)
        elif upload.status in ("PROCESSING", "COMPLETED"):
            raise InvalidStateError(f"Log file is already {upload.status.lower()}; nothing to retry")
        return upload

    def delete_upload(self, user: User, upload_id: int, ip: str | None) -> None:
        upload = self._get(user, upload_id)
        if upload.status == "PROCESSING":
            raise InvalidStateError("Cannot delete a log file while it is being processed")
        path = self.upload_root / upload.stored_path
        self.repo.delete_upload(upload)
        self.audit.record("log.deleted", user.id, ip, "log_upload", str(upload_id))
        self.db.commit()
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove stored file for deleted upload %s", upload_id)
