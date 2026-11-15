"""Incident report generation and download (PDF / CSV / JSON)."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.models.document import Report
from app.models.incident import AIInvestigation, AnomalyDetection, IncidentLogLink
from app.models.log import LogEntry
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.schemas.knowledge import ReportRead
from app.schemas.log import Page
from app.services.incident_logic import incident_public_id
from app.services.incident_service import IncidentService, aware
from app.services.report_builder import ReportData, build_csv, build_json, build_pdf

MEDIA_TYPES = {"pdf": "application/pdf", "csv": "text/csv", "json": "application/json"}


class ReportService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db, self.settings = db, settings
        self.incidents = IncidentService(db, settings)

    def _data(self, user: User, incident_id: int) -> tuple[ReportData, str]:
        inc = self.incidents.get(user, incident_id)
        read = self.incidents.read(inc)
        logs = self.db.execute(
            select(LogEntry.timestamp, LogEntry.level, LogEntry.service, LogEntry.message)
            .join(IncidentLogLink, IncidentLogLink.log_entry_id == LogEntry.id)
            .where(IncidentLogLink.incident_id == inc.id, LogEntry.user_id == user.id)
            .order_by(LogEntry.timestamp).limit(200)
        ).all()
        anomalies = []
        if inc.upload_id and inc.first_occurrence and inc.last_occurrence:
            rows = self.db.scalars(
                select(AnomalyDetection).where(
                    AnomalyDetection.upload_id == inc.upload_id, AnomalyDetection.user_id == user.id,
                    AnomalyDetection.anomaly_detected.is_(True))
                .order_by(AnomalyDetection.window_start).limit(50)
            ).all()
            lo, hi = aware(inc.first_occurrence), aware(inc.last_occurrence)
            anomalies = [{"window_start": r.window_start, "anomaly_score": r.anomaly_score, "threshold": r.threshold,
                          "method": r.method, "affected_service": r.affected_service}
                         for r in rows if aware(r.window_end) >= lo and aware(r.window_start) <= hi]  # type: ignore[operator]
        latest = self.db.scalar(select(AIInvestigation).where(AIInvestigation.incident_id == inc.id, AIInvestigation.status == "COMPLETED")
                                .order_by(AIInvestigation.id.desc()).limit(1))
        notes = self.incidents.detail(user, incident_id).notes
        incident = read.model_dump()
        incident["sample_size_note"] = "Supporting logs are limited to linked error-level entries."
        data = ReportData(
            incident=incident,
            timeline=[e.model_dump() for e in self.incidents.timeline(user, incident_id, None, None, None)],
            logs=[{"timestamp": t, "level": lv, "service": s, "message": m} for t, lv, s, m in logs],
            anomalies=anomalies,
            similar_incidents=[s.model_dump() for s in self.incidents._related(inc)],
            ai_investigation=latest.result if latest else None,
            human_notes=[{"author": n.author_name or "unknown", "timestamp": n.created_at, "content": n.content} for n in notes],
            generated_at=datetime.now(UTC), generated_by=user.email,
        )
        return data, incident_public_id(inc.id)

    def generate(self, user: User, incident_id: int, fmt: str, ip: str | None) -> Report:
        data, public_id = self._data(user, incident_id)
        content = {"pdf": build_pdf, "csv": build_csv, "json": build_json}[fmt](data)
        directory = Path(self.settings.reports_dir) / str(user.id)
        directory.mkdir(parents=True, exist_ok=True)
        stored = directory / f"{uuid.uuid4().hex}.{fmt}"
        stored.write_bytes(content)
        report = Report(user_id=user.id, incident_id=incident_id, format=fmt,
                        filename=f"incident-{public_id}-{datetime.now(UTC):%Y%m%d-%H%M%S}.{fmt}",
                        stored_path=f"{user.id}/{stored.name}", size_bytes=len(content))
        self.db.add(report)
        self.db.flush()
        AuditRepository(self.db).record("report.generated", user.id, ip, "report", str(report.id), {"format": fmt})
        self.db.commit()
        return report

    def list_reports(self, user: User, page: int, page_size: int) -> Page[ReportRead]:
        stmt = select(Report).where(Report.user_id == user.id)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = self.db.scalars(stmt.order_by(Report.created_at.desc(), Report.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return Page(items=[ReportRead.model_validate(r) for r in rows], total=total, page=page, page_size=page_size)

    def file_for_download(self, user: User, report_id: int) -> tuple[Report, Path]:
        report = self.db.scalar(select(Report).where(Report.id == report_id, Report.user_id == user.id))
        if report is None:
            raise NotFoundError("Report not found")
        path = Path(self.settings.reports_dir) / report.stored_path
        if not path.is_file():
            raise NotFoundError("The report file is no longer available")
        return report, path
