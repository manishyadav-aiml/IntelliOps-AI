from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.log import LogEntry, LogTemplate, LogUpload

UPLOAD_SORT = {"created_at": LogUpload.created_at, "filename": LogUpload.filename, "size_bytes": LogUpload.size_bytes}
ENTRY_SORT = {"line_number": LogEntry.line_number, "timestamp": LogEntry.timestamp, "level": LogEntry.level}


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class LogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- uploads (every query is scoped to the owning user) ----
    def add_upload(self, upload: LogUpload) -> LogUpload:
        self.db.add(upload)
        self.db.flush()
        return upload

    def get_upload(self, user_id: int, upload_id: int) -> LogUpload | None:
        return self.db.scalar(
            select(LogUpload).where(LogUpload.id == upload_id, LogUpload.user_id == user_id)
        )

    def list_uploads(
        self, user_id: int, page: int, page_size: int, status: str | None, q: str | None,
        sort_by: str, descending: bool,
    ) -> tuple[list[LogUpload], int]:
        stmt = select(LogUpload).where(LogUpload.user_id == user_id)
        if status:
            stmt = stmt.where(LogUpload.status == status)
        if q:
            stmt = stmt.where(LogUpload.filename.ilike(_like(q), escape="\\"))
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        column = UPLOAD_SORT.get(sort_by, LogUpload.created_at)
        stmt = stmt.order_by(column.desc() if descending else column.asc(), LogUpload.id.desc())
        rows = self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        return list(rows), total

    def claim_for_processing(self, upload_id: int, now: datetime) -> bool:
        """Atomically PENDING -> PROCESSING. Returns False if another worker already claimed it."""
        result = self.db.execute(
            update(LogUpload)
            .where(LogUpload.id == upload_id, LogUpload.status == "PENDING")
            .values(status="PROCESSING", started_at=now, error_message=None, processed_lines=0)
        )
        self.db.commit()
        return result.rowcount == 1

    def reset_failed_to_pending(self, upload_id: int) -> bool:
        result = self.db.execute(
            update(LogUpload)
            .where(LogUpload.id == upload_id, LogUpload.status == "FAILED")
            .values(status="PENDING", error_message=None)
        )
        self.db.commit()
        return result.rowcount == 1

    def delete_entries(self, upload_id: int) -> None:
        self.db.execute(delete(LogEntry).where(LogEntry.upload_id == upload_id))

    def delete_upload(self, upload: LogUpload) -> None:
        self.delete_entries(upload.id)
        self.db.delete(upload)

    # ---- templates ----
    def get_or_create_template(self, user_id: int, template_hash: str, text: str) -> int:
        existing = self.db.scalar(
            select(LogTemplate.id).where(
                LogTemplate.user_id == user_id, LogTemplate.template_hash == template_hash
            )
        )
        if existing is not None:
            return existing
        try:
            template = LogTemplate(user_id=user_id, template_hash=template_hash, template_text=text)
            self.db.add(template)
            self.db.commit()  # committed immediately: nothing else is pending, so a rollback is safe
            return template.id
        except IntegrityError:  # created concurrently by another upload of the same user
            self.db.rollback()
            found = self.db.scalar(
                select(LogTemplate.id).where(
                    LogTemplate.user_id == user_id, LogTemplate.template_hash == template_hash
                )
            )
            if found is None:
                raise
            return found

    def top_templates(self, user_id: int, upload_id: int, limit: int) -> list[tuple[LogTemplate, int]]:
        count = func.count(LogEntry.id)
        rows = self.db.execute(
            select(LogTemplate, count)
            .join(LogEntry, LogEntry.template_id == LogTemplate.id)
            .where(LogEntry.upload_id == upload_id, LogEntry.user_id == user_id)
            .group_by(LogTemplate.id)
            .order_by(count.desc(), LogTemplate.id)
            .limit(limit)
        ).all()
        return [(t, c) for t, c in rows]

    # ---- entries ----
    def bulk_insert_entries(self, rows: list[dict[str, Any]]) -> None:
        if rows:
            self.db.execute(insert(LogEntry), rows)

    def list_entries(
        self, user_id: int, upload_id: int, page: int, page_size: int, level: str | None,
        service: str | None, template_id: int | None, q: str | None, start: datetime | None,
        end: datetime | None, sort_by: str, descending: bool,
    ) -> tuple[list[tuple[LogEntry, str | None]], int]:
        conditions = [LogEntry.upload_id == upload_id, LogEntry.user_id == user_id]
        if level:
            conditions.append(LogEntry.level == level.upper())
        if service:
            conditions.append(LogEntry.service == service)
        if template_id is not None:
            conditions.append(LogEntry.template_id == template_id)
        if q:
            conditions.append(LogEntry.message.ilike(_like(q), escape="\\"))
        if start:
            conditions.append(LogEntry.timestamp >= start)
        if end:
            conditions.append(LogEntry.timestamp <= end)
        total = self.db.scalar(select(func.count()).select_from(LogEntry).where(*conditions)) or 0
        column = ENTRY_SORT.get(sort_by, LogEntry.line_number)
        stmt = (
            select(LogEntry, LogTemplate.template_text)
            .outerjoin(LogTemplate, LogEntry.template_id == LogTemplate.id)
            .where(*conditions)
            .order_by(column.desc() if descending else column.asc(), LogEntry.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return [(e, t) for e, t in self.db.execute(stmt).all()], total

    def facets(self, user_id: int, upload_id: int) -> tuple[list[str], list[str]]:
        base = (LogEntry.upload_id == upload_id, LogEntry.user_id == user_id)
        levels = self.db.scalars(select(LogEntry.level).where(*base).distinct().order_by(LogEntry.level)).all()
        services = self.db.scalars(
            select(LogEntry.service).where(*base).distinct().order_by(LogEntry.service).limit(200)
        ).all()
        return list(levels), list(services)
