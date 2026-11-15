from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class AnomalyDetection(TimestampMixin, Base):
    """One scored time window of one upload. `anomaly_score` is NOT a probability."""

    __tablename__ = "anomaly_detections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    upload_id: Mapped[int] = mapped_column(ForeignKey("log_uploads.id", ondelete="CASCADE"), index=True, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    anomaly_detected: Mapped[bool] = mapped_column(Boolean, index=True, nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    affected_service: Mapped[str] = mapped_column(String(128), nullable=False)
    contributing_features: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    detection_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Incident(TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint("severity IN ('P1', 'P2', 'P3', 'P4')", name="severity_valid"),
        CheckConstraint("status IN ('OPEN', 'INVESTIGATING', 'MITIGATED', 'RESOLVED')", name="status_valid"),
        UniqueConstraint("user_id", "fingerprint"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    upload_id: Mapped[int | None] = mapped_column(ForeignKey("log_uploads.id", ondelete="SET NULL"), index=True, nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(32), nullable=True)  # NULL for manual incidents
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    service: Mapped[str] = mapped_column(String(128), index=True, default="unknown", nullable=False)
    severity: Mapped[str] = mapped_column(String(2), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), index=True, default="OPEN", nullable=False)
    severity_reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    services: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    templates: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    error_templates: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    anomaly_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    detection_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_occurrence: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_occurrence: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IncidentEvent(Base):
    """Timeline entry. Only real, stored timestamps; missing events are never fabricated."""

    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IncidentNote(TimestampMixin, Base):
    __tablename__ = "incident_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class IncidentLogLink(Base):
    __tablename__ = "incident_log_links"
    __table_args__ = (UniqueConstraint("incident_id", "log_entry_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    log_entry_id: Mapped[int] = mapped_column(ForeignKey("log_entries.id", ondelete="CASCADE"), nullable=False)


class IncidentRelationship(TimestampMixin, Base):
    """Similarity link. Similarity is NOT proof of a common root cause."""

    __tablename__ = "incident_relationships"
    __table_args__ = (UniqueConstraint("incident_id", "related_incident_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    related_incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    shared: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class AIInvestigation(TimestampMixin, Base):
    __tablename__ = "ai_investigations"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # COMPLETED | FAILED
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
