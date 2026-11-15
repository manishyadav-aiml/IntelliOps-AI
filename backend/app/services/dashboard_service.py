"""Dashboard queries. Every number comes from the database; empty data yields zeros/nulls, never demo values."""

from datetime import datetime

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models.incident import AnomalyDetection, Incident
from app.models.log import LogEntry, LogTemplate, LogUpload
from app.models.user import User
from app.schemas.knowledge import Bucket, DashboardSummary, DashboardTrends, NamedCount
from app.services.dashboard_logic import average_seconds, bucket_counts, distribution, fill_gaps
from app.services.incident_service import aware

ROW_CAP = 200_000


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self, user: User, start: datetime | None, end: datetime | None, service: str | None) -> DashboardSummary:
        up = select(LogUpload).where(LogUpload.user_id == user.id, LogUpload.status == "COMPLETED")
        if start:
            up = up.where(LogUpload.created_at >= start)
        if end:
            up = up.where(LogUpload.created_at <= end)
        total_logs = self.db.scalar(select(func.coalesce(func.sum(up.subquery().c.entry_count), 0))) or 0
        uploads_total = self.db.scalar(select(func.count()).select_from(LogUpload).where(LogUpload.user_id == user.id)) or 0

        inc = select(Incident).where(Incident.user_id == user.id)
        if service:
            inc = inc.where(Incident.service == service)
        if start:
            inc = inc.where(Incident.detection_time >= start)
        if end:
            inc = inc.where(Incident.detection_time <= end)
        incidents = list(self.db.scalars(inc))
        anomalies = select(func.count()).select_from(AnomalyDetection).where(
            AnomalyDetection.user_id == user.id, AnomalyDetection.anomaly_detected.is_(True))
        if service:
            anomalies = anomalies.where(AnomalyDetection.affected_service == service)
        if start:
            anomalies = anomalies.where(AnomalyDetection.window_start >= start)
        if end:
            anomalies = anomalies.where(AnomalyDetection.window_start <= end)
        services = self.db.scalar(select(func.count(distinct(LogEntry.service))).where(
            LogEntry.user_id == user.id, LogEntry.service != "unknown")) or 0
        return DashboardSummary(
            total_logs_processed=int(total_logs), uploads_total=uploads_total,
            active_incidents=sum(i.status != "RESOLVED" for i in incidents),
            critical_incidents=sum(i.severity == "P1" and i.status != "RESOLVED" for i in incidents),
            anomalies_detected=self.db.scalar(anomalies) or 0, services_monitored=services,
            resolved_incidents=sum(i.status == "RESOLVED" for i in incidents),
            avg_time_to_acknowledge_seconds=average_seconds((aware(i.detection_time), aware(i.acknowledged_at)) for i in incidents),
            avg_time_to_resolve_seconds=average_seconds((aware(i.detection_time), aware(i.resolved_at)) for i in incidents),
        )

    def trends(self, user: User, bucket: str, start: datetime | None, end: datetime | None, service: str | None) -> DashboardTrends:
        errors = select(LogEntry.timestamp).where(
            LogEntry.user_id == user.id, LogEntry.level.in_(["ERROR", "CRITICAL"]), LogEntry.timestamp.is_not(None))
        if service:
            errors = errors.where(LogEntry.service == service)
        if start:
            errors = errors.where(LogEntry.timestamp >= start)
        if end:
            errors = errors.where(LogEntry.timestamp <= end)
        error_ts = [aware(t) for t in self.db.scalars(errors.limit(ROW_CAP + 1))]
        truncated = len(error_ts) > ROW_CAP
        error_ts = error_ts[:ROW_CAP]

        anomalies = select(AnomalyDetection.window_start).where(AnomalyDetection.user_id == user.id, AnomalyDetection.anomaly_detected.is_(True))
        inc = select(Incident).where(Incident.user_id == user.id)
        if service:
            anomalies = anomalies.where(AnomalyDetection.affected_service == service)
            inc = inc.where(Incident.service == service)
        if start:
            anomalies = anomalies.where(AnomalyDetection.window_start >= start)
        if end:
            anomalies = anomalies.where(AnomalyDetection.window_start <= end)
        incidents = list(self.db.scalars(inc))
        anomaly_ts = [aware(t) for t in self.db.scalars(anomalies)]
        resolved_ts = [aware(i.resolved_at) for i in incidents if i.resolved_at]

        def series(values: list) -> list[Bucket]:
            points = bucket_counts(values, bucket)
            if start and end and points:
                points = fill_gaps(points, bucket, aware(start), aware(end))  # type: ignore[arg-type]
            return [Bucket(**p) for p in points]

        template_rows = self.db.execute(
            select(LogTemplate.template_text, func.count(LogEntry.id).label("n"))
            .join(LogEntry, LogEntry.template_id == LogTemplate.id)
            .where(LogEntry.user_id == user.id, *( [LogEntry.service == service] if service else []))
            .group_by(LogTemplate.id).order_by(func.count(LogEntry.id).desc()).limit(10)
        ).all()
        return DashboardTrends(
            bucket=bucket, error_frequency=series(error_ts), anomaly_trend=series(anomaly_ts),
            resolution_trend=series(resolved_ts), truncated=truncated,
            severity_distribution=[NamedCount(**d) for d in distribution(i.severity for i in incidents)],
            top_templates=[NamedCount(name=t, count=n) for t, n in template_rows],
        )

    def services(self, user: User) -> list[NamedCount]:
        rows = self.db.execute(select(Incident.service, func.count(Incident.id)).where(Incident.user_id == user.id)
                               .group_by(Incident.service).order_by(func.count(Incident.id).desc())).all()
        return [NamedCount(name=s, count=n) for s, n in rows]
