"""Run anomaly detection for one parsed upload and turn anomalous windows into incidents."""

from pathlib import Path

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import InvalidStateError, NotFoundError, ValidationAppError
from app.ml.anomaly_detection import detect_anomalies
from app.ml.feature_engineering import build_window_features
from app.ml.preprocessing import LogRow, prepare_frame
from app.models.incident import AnomalyDetection
from app.models.log import LogEntry, LogUpload
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.schemas.incident import AnalysisResult, AnomalyRead
from app.schemas.log import Page
from app.services.incident_logic import group_anomalous_windows
from app.services.incident_service import IncidentService

MAX_ROWS = 1_000_000


class AnomalyService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.incidents = IncidentService(db, settings)

    def run(self, user: User, upload_id: int, window_seconds: int | None, ip: str | None) -> AnalysisResult:
        upload = self.db.scalar(select(LogUpload).where(LogUpload.id == upload_id, LogUpload.user_id == user.id))
        if upload is None:
            raise NotFoundError("Log file not found")
        if upload.status != "COMPLETED":
            raise InvalidStateError("Anomaly detection needs a fully parsed log file (status COMPLETED)")
        window = window_seconds or self.settings.anomaly_window_seconds
        if not 10 <= window <= 3600:
            raise ValidationAppError("window_seconds must be between 10 and 3600")

        stmt = (select(LogEntry.timestamp, LogEntry.level, LogEntry.service, LogEntry.template_id)
                .where(LogEntry.upload_id == upload.id, LogEntry.user_id == user.id).limit(MAX_ROWS))
        rows = (LogRow(ts, level, service, str(template)) for ts, level, service, template in self.db.execute(stmt))
        frame, dropped = prepare_frame(rows)
        try:
            feats = build_window_features(frame, window)
        except ValueError as exc:
            raise ValidationAppError(str(exc)) from exc
        results, method = detect_anomalies(feats, window, Path(self.settings.models_dir), self.settings.anomaly_threshold)

        self.db.execute(delete(AnomalyDetection).where(AnomalyDetection.upload_id == upload.id, AnomalyDetection.user_id == user.id))
        if results:
            self.db.execute(insert(AnomalyDetection), [
                {"user_id": user.id, "upload_id": upload.id, "window_start": r.window_start, "window_end": r.window_end,
                 "anomaly_detected": r.anomaly_detected, "anomaly_score": r.anomaly_score, "threshold": r.threshold,
                 "method": r.method, "model_version": r.model_version, "affected_service": r.affected_service[:128],
                 "contributing_features": r.contributing_features, "features": r.features,
                 "detection_timestamp": r.detection_timestamp}
                for r in results
            ])
        AuditRepository(self.db).record("anomaly.analysis_run", user.id, ip, "log_upload", str(upload.id),
                                        {"method": method, "windows": len(results)})
        self.db.commit()

        candidates = group_anomalous_windows(results, window)
        created, updated = self.incidents.upsert_from_candidates(user, upload, candidates, window, method, ip)
        return AnalysisResult(
            upload_id=upload.id, method=method, window_seconds=window, windows_analyzed=len(results),
            anomalous_windows=sum(r.anomaly_detected for r in results), entries_without_timestamp=dropped,
            incidents_created=len(created), incidents_updated=len(updated), incident_ids=[i.id for i in [*created, *updated]],
        )

    def list_anomalies(self, user: User, page: int, page_size: int, upload_id: int | None, detected_only: bool,
                       sort_by: str, descending: bool) -> Page[AnomalyRead]:
        stmt = select(AnomalyDetection).where(AnomalyDetection.user_id == user.id)
        if upload_id is not None:
            stmt = stmt.where(AnomalyDetection.upload_id == upload_id)
        if detected_only:
            stmt = stmt.where(AnomalyDetection.anomaly_detected.is_(True))
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        column = AnomalyDetection.anomaly_score if sort_by == "anomaly_score" else AnomalyDetection.window_start
        stmt = stmt.order_by(column.desc() if descending else column.asc(), AnomalyDetection.id)
        rows = self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        return Page(items=[AnomalyRead.model_validate(r) for r in rows], total=total, page=page, page_size=page_size)

    def get_anomaly(self, user: User, anomaly_id: int) -> AnomalyDetection:
        row = self.db.scalar(select(AnomalyDetection).where(AnomalyDetection.id == anomaly_id, AnomalyDetection.user_id == user.id))
        if row is None:
            raise NotFoundError("Anomaly record not found")
        return row
