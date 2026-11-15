from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin

UPLOAD_STATUSES = ("PENDING", "PROCESSING", "COMPLETED", "FAILED")


class LogUpload(TimestampMixin, Base):
    """One uploaded log file. `stored_path` is relative to UPLOAD_DIR and server-generated."""

    __tablename__ = "log_uploads"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')", name="status_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    extension: Mapped[str] = mapped_column(String(8), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True, nullable=False)
    total_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    entry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_stats: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    parser_used: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LogTemplate(TimestampMixin, Base):
    """A log template (e.g. 'User <*> connected to server <*>'), unique per user."""

    __tablename__ = "log_templates"
    __table_args__ = (UniqueConstraint("user_id", "template_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    template_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)


class LogEntry(Base):
    """One parsed log line. `original_message` always keeps the raw line."""

    __tablename__ = "log_entries"
    __table_args__ = (UniqueConstraint("upload_id", "line_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(
        ForeignKey("log_uploads.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    level: Mapped[str] = mapped_column(String(16), default="UNKNOWN", index=True, nullable=False)
    service: Mapped[str] = mapped_column(String(128), default="unknown", index=True, nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), default="unknown", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    original_message: Mapped[str] = mapped_column(Text, nullable=False)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("log_templates.id", ondelete="SET NULL"), index=True, nullable=True
    )
    parameters: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    truncated: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
