"""Incident lifecycle: creation from anomalies (grouped + de-duplicated), updates, notes, timeline."""

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import InvalidStateError, NotFoundError, ValidationAppError
from app.ml.root_cause import analyze_incident
from app.ml.severity_classifier import SEVERITY_LABELS, SeverityInput, classify_severity
from app.models.incident import (
    AIInvestigation,
    Incident,
    IncidentEvent,
    IncidentLogLink,
    IncidentNote,
    IncidentRelationship,
)
from app.models.log import LogEntry, LogTemplate, LogUpload
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.schemas.incident import (
    EventRead,
    IncidentCreate,
    IncidentDetail,
    IncidentRead,
    IncidentUpdate,
    InvestigationRead,
    NoteRead,
    SimilarRead,
)
from app.schemas.log import Page
from app.services.incident_logic import (
    IncidentCandidate,
    InvalidTransitionError,
    fingerprint,
    incident_public_id,
    ranges_overlap,
    stats_for_entries,
    validate_transition,
)
from app.services.similarity_index import SimilarityIndexService

SORTABLE = {"created_at": Incident.created_at, "detection_time": Incident.detection_time,
            "severity": Incident.severity, "status": Incident.status}
STATUS_EVENT = {"INVESTIGATING": "INVESTIGATION_STARTED", "MITIGATED": "MITIGATED", "RESOLVED": "RESOLVED", "OPEN": "REOPENED"}
MAX_LINKED_LOGS = 50
MAX_RANGE_ROWS = 20_000


def aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC so comparisons never mix naive/aware."""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class IncidentService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.audit = AuditRepository(db)
        self.index = SimilarityIndexService(db, settings)

    # ---------- helpers ----------
    def get(self, user: User, incident_id: int) -> Incident:
        incident = self.db.scalar(select(Incident).where(Incident.id == incident_id, Incident.user_id == user.id))
        if incident is None:
            raise NotFoundError("Incident not found")
        return incident

    def _event(self, incident_id: int, event_type: str, ts: datetime, description: str,
               actor: int | None = None, details: dict[str, Any] | None = None) -> None:
        self.db.add(IncidentEvent(incident_id=incident_id, event_type=event_type, timestamp=ts,
                                  description=description, actor_user_id=actor, details=details))

    def read(self, inc: Incident) -> IncidentRead:
        assignee = self.db.get(User, inc.assigned_user_id) if inc.assigned_user_id else None
        return IncidentRead(
            id=inc.id, public_id=incident_public_id(inc.id), title=inc.title, description=inc.description,
            service=inc.service, severity=inc.severity, severity_label=SEVERITY_LABELS[inc.severity],
            severity_reasons=inc.severity_reasons or [], status=inc.status, services=inc.services or [],
            upload_id=inc.upload_id, detection_time=inc.detection_time, first_occurrence=inc.first_occurrence,
            last_occurrence=inc.last_occurrence, assigned_user_id=inc.assigned_user_id,
            assigned_to=assignee.full_name if assignee else None, resolution_notes=inc.resolution_notes,
            acknowledged_at=inc.acknowledged_at, resolved_at=inc.resolved_at, created_at=inc.created_at,
            updated_at=inc.updated_at, anomaly_summary=inc.anomaly_summary,
        )

    def _related(self, incident: Incident) -> list[SimilarRead]:
        rows = self.db.scalars(
            select(IncidentRelationship).where(IncidentRelationship.incident_id == incident.id)
            .order_by(IncidentRelationship.similarity_score.desc())
        ).all()
        out = []
        for row in rows:
            other = self.db.scalar(select(Incident).where(Incident.id == row.related_incident_id, Incident.user_id == incident.user_id))
            if other is None:
                continue
            out.append(SimilarRead(
                incident_id=incident_public_id(incident.id), similar_incident_id=incident_public_id(other.id),
                similar_incident_pk=other.id, title=other.title, similarity_score=row.similarity_score,
                shared_services=row.shared.get("services", []), shared_templates=row.shared.get("templates", []),
                shared_error_patterns=row.shared.get("error_patterns", []),
                note="Similarity indicates comparable symptoms, not a confirmed common root cause.",
            ))
        return out

    def detail(self, user: User, incident_id: int) -> IncidentDetail:
        inc = self.get(user, incident_id)
        notes = []
        for note in self.db.scalars(select(IncidentNote).where(IncidentNote.incident_id == inc.id).order_by(IncidentNote.created_at)):
            author = self.db.get(User, note.author_id) if note.author_id else None
            notes.append(NoteRead(id=note.id, author_id=note.author_id, author_name=author.full_name if author else None,
                                  content=note.content, created_at=note.created_at))
        latest = self.db.scalar(select(AIInvestigation).where(AIInvestigation.incident_id == inc.id)
                                .order_by(AIInvestigation.id.desc()).limit(1))
        linked = self.db.scalar(select(func.count()).select_from(IncidentLogLink).where(IncidentLogLink.incident_id == inc.id)) or 0
        return IncidentDetail(**self.read(inc).model_dump(), templates=inc.templates or [], notes=notes,
                              related=self._related(inc),
                              latest_investigation=InvestigationRead.model_validate(latest) if latest else None,
                              linked_log_count=linked)

    def list_incidents(self, user: User, page: int, page_size: int, status: str | None, severity: str | None,
             service: str | None, q: str | None, sort_by: str, descending: bool) -> Page[IncidentRead]:
        stmt = select(Incident).where(Incident.user_id == user.id)
        if status:
            stmt = stmt.where(Incident.status == status)
        if severity:
            stmt = stmt.where(Incident.severity == severity)
        if service:
            stmt = stmt.where(Incident.service == service)
        if q:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(Incident.title.ilike(f"%{escaped}%", escape="\\"))
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        column = SORTABLE.get(sort_by, Incident.created_at)
        stmt = stmt.order_by(column.desc() if descending else column.asc(), Incident.id.desc())
        rows = self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        return Page(items=[self.read(r) for r in rows], total=total, page=page, page_size=page_size)

    # ---------- manual creation ----------
    def create_manual(self, user: User, data: IncidentCreate, ip: str | None) -> Incident:
        if data.upload_id is not None:
            upload = self.db.scalar(select(LogUpload).where(LogUpload.id == data.upload_id, LogUpload.user_id == user.id))
            if upload is None:
                raise NotFoundError("Log file not found")
        now = datetime.now(UTC)
        incident = Incident(
            user_id=user.id, upload_id=data.upload_id, title=data.title, description=data.description,
            service=data.service, severity=data.severity, status="OPEN",
            severity_reasons=[f"Severity set manually by {user.full_name}"], services=[data.service],
            templates=[], error_templates=[], detection_time=now,
            first_occurrence=data.first_occurrence, last_occurrence=data.last_occurrence,
        )
        self.db.add(incident)
        self.db.flush()
        self._event(incident.id, "INCIDENT_CREATED", now, f"Incident created manually by {user.full_name}",
                    user.id, {"severity": data.severity})
        self.audit.record("incident.created", user.id, ip, "incident", str(incident.id))
        self.db.commit()
        self.index.upsert(incident)
        return incident

    # ---------- updates ----------
    def update(self, user: User, incident_id: int, payload: IncidentUpdate, ip: str | None) -> Incident:
        inc = self.get(user, incident_id)
        changed = payload.model_fields_set
        now = datetime.now(UTC)
        retitle = False
        if "title" in changed and payload.title is not None:
            retitle = payload.title != inc.title
            inc.title = payload.title.strip()
        if "description" in changed and payload.description is not None:
            inc.description = payload.description
        if "resolution_notes" in changed:
            inc.resolution_notes = payload.resolution_notes
        if "severity" in changed and payload.severity and payload.severity != inc.severity:
            old, inc.severity = inc.severity, payload.severity
            self._event(inc.id, "SEVERITY_CHANGED", now, f"Severity changed from {old} to {inc.severity} by {user.full_name}",
                        user.id, {"from": old, "to": inc.severity})
            self.audit.record("incident.severity_changed", user.id, ip, "incident", str(inc.id),
                              {"from": old, "to": inc.severity})
        if "status" in changed and payload.status and payload.status != inc.status:
            try:
                validate_transition(inc.status, payload.status)
            except InvalidTransitionError as exc:
                raise InvalidStateError(str(exc)) from exc
            old, inc.status = inc.status, payload.status
            if old == "OPEN" and inc.acknowledged_at is None:
                inc.acknowledged_at = now
            if inc.status == "RESOLVED":
                inc.resolved_at = now
            elif old == "RESOLVED":
                inc.resolved_at = None
            self._event(inc.id, STATUS_EVENT[inc.status], now, f"Status changed from {old} to {inc.status} by {user.full_name}",
                        user.id, {"from": old, "to": inc.status})
            self.audit.record("incident.status_changed", user.id, ip, "incident", str(inc.id), {"from": old, "to": inc.status})
        if "assigned_user_id" in changed:
            if payload.assigned_user_id not in (None, user.id):
                raise ValidationAppError("Incidents can only be assigned to yourself (multi-user teams are not implemented)")
            if payload.assigned_user_id != inc.assigned_user_id:
                inc.assigned_user_id = payload.assigned_user_id
                text = f"Assigned to {user.full_name}" if payload.assigned_user_id else "Unassigned"
                self._event(inc.id, "ASSIGNED", now, text, user.id)
                self.audit.record("incident.assigned", user.id, ip, "incident", str(inc.id))
        self.db.commit()
        if retitle:
            self.index.upsert(inc)
        return inc

    def add_note(self, user: User, incident_id: int, content: str, ip: str | None) -> IncidentNote:
        inc = self.get(user, incident_id)
        note = IncidentNote(incident_id=inc.id, author_id=user.id, content=content.strip())
        self.db.add(note)
        self._event(inc.id, "NOTE_ADDED", datetime.now(UTC), f"Investigation note added by {user.full_name}", user.id)
        self.audit.record("incident.note_added", user.id, ip, "incident", str(inc.id))
        self.db.commit()
        return note

    def timeline(self, user: User, incident_id: int, event_types: list[str] | None,
                 start: datetime | None, end: datetime | None) -> list[EventRead]:
        inc = self.get(user, incident_id)
        stmt = select(IncidentEvent).where(IncidentEvent.incident_id == inc.id)
        if event_types:
            stmt = stmt.where(IncidentEvent.event_type.in_(event_types))
        if start:
            stmt = stmt.where(IncidentEvent.timestamp >= start)
        if end:
            stmt = stmt.where(IncidentEvent.timestamp <= end)
        return [EventRead.model_validate(e) for e in self.db.scalars(stmt.order_by(IncidentEvent.timestamp, IncidentEvent.id))]

    def similar(self, user: User, incident_id: int) -> list[SimilarRead]:
        inc = self.get(user, incident_id)
        self.index.refresh_relationships(inc)
        self.db.commit()
        return self._related(inc)

    # ---------- creation from anomaly candidates ----------
    def _entries(self, user_id: int, upload_id: int, start: datetime, end: datetime) -> list[tuple]:
        stmt = (select(LogEntry.id, LogEntry.level, LogEntry.service, LogEntry.template_id, LogEntry.timestamp)
                .where(LogEntry.upload_id == upload_id, LogEntry.user_id == user_id,
                       LogEntry.timestamp >= start, LogEntry.timestamp < end)
                .order_by(LogEntry.timestamp).limit(MAX_RANGE_ROWS))
        return [tuple(r) for r in self.db.execute(stmt).all()]

    def _template_texts(self, entries: list[tuple]) -> tuple[list[str], list[str]]:
        def top(rows: list[tuple]) -> list[str]:
            counts = Counter(r[3] for r in rows if r[3] is not None)
            ids = [i for i, _ in counts.most_common(10)]
            if not ids:
                return []
            text = dict(self.db.execute(select(LogTemplate.id, LogTemplate.template_text).where(LogTemplate.id.in_(ids))).all())
            return [text[i] for i in ids if i in text]

        errors = [r for r in entries if r[1] in ("ERROR", "CRITICAL")]
        return top(errors or entries), top(errors)

    def _rca(self, user_id: int, upload_id: int, start: datetime, end: datetime) -> dict[str, Any]:
        """Deterministic root-cause evidence from the 30 minutes before the incident plus the incident itself."""
        lookback = timedelta(minutes=30)
        stmt = (select(LogEntry.timestamp, LogEntry.level, LogEntry.service, LogTemplate.template_text)
                .join(LogTemplate, LogEntry.template_id == LogTemplate.id, isouter=True)
                .where(LogEntry.upload_id == upload_id, LogEntry.user_id == user_id,
                       LogEntry.timestamp >= start - lookback, LogEntry.timestamp < end)
                .order_by(LogEntry.timestamp).limit(50_000))
        rows = [(aware(ts), level, service, text or "<unknown template>") for ts, level, service, text in self.db.execute(stmt).all()]
        return analyze_incident(rows, start, end, lookback).to_dict()

    def _historical_p1_matches(self, user_id: int, error_templates: list[str]) -> int:
        if not error_templates:
            return 0
        mine = set(error_templates)
        rows = self.db.scalars(select(Incident.error_templates).where(Incident.user_id == user_id, Incident.severity == "P1"))
        return sum(1 for templates in rows if mine & set(templates or []))

    def upsert_from_candidates(self, user: User, upload: LogUpload, candidates: list[IncidentCandidate],
                               window_seconds: int, method: str, ip: str | None = None) -> tuple[list[Incident], list[Incident]]:
        created: list[Incident] = []
        updated: list[Incident] = []
        grace = timedelta(seconds=window_seconds * 2)
        for cand in candidates:
            start, end = aware(cand.start), aware(cand.end)
            assert start is not None and end is not None
            fp = fingerprint(user.id, upload.id, cand.primary_service, start)
            incident = self.db.scalar(select(Incident).where(Incident.user_id == user.id, Incident.fingerprint == fp))
            if incident is None:  # merge into an overlapping incident of the same service instead of duplicating
                for other in self.db.scalars(select(Incident).where(
                        Incident.user_id == user.id, Incident.upload_id == upload.id, Incident.service == cand.primary_service)):
                    o_start = aware(other.first_occurrence or other.detection_time)
                    o_end = aware(other.last_occurrence) or o_start
                    if ranges_overlap(o_start, o_end, start, end, grace):  # type: ignore[arg-type]
                        incident = other
                        break
            entries = self._entries(user.id, upload.id, start, end)
            if incident is None:
                created.append(self._create_from_candidate(user, upload, cand, fp, entries, method))
            elif self._refresh(incident, cand, entries, method):
                updated.append(incident)
        self.audit.record("incident.auto_created", user.id, ip, "log_upload", str(upload.id),
                          {"created": len(created), "updated": len(updated)})
        self.db.commit()
        for incident in [*created, *updated]:
            self.index.upsert(incident)
            self.index.refresh_relationships(incident)
        self.db.commit()
        return created, updated

    def _summary(self, cand: IncidentCandidate, method: str) -> dict[str, Any]:
        first = cand.detections[0]
        return {"anomalous_windows": cand.window_count, "max_score": cand.max_score, "threshold": first.threshold,
                "method": method, "model_version": first.model_version, "contributing_features": first.contributing_features,
                "note": "anomaly_score is model-specific and is not a probability."}

    def _create_from_candidate(self, user: User, upload: LogUpload, cand: IncidentCandidate, fp: str,
                               entries: list[tuple], method: str) -> Incident:
        stats = stats_for_entries((e[1], e[2]) for e in entries)
        templates, error_templates = self._template_texts(entries)
        first = cand.detections[0]
        severity = classify_severity(SeverityInput(
            error_count=stats.error_count, critical_count=stats.critical_count, total_events=stats.total_events,
            affected_services=len(stats.error_services) or max(1, len(stats.services)),
            anomaly_score=cand.max_score, anomaly_threshold=first.threshold,
            duration_seconds=(cand.end - cand.start).total_seconds(),
            historical_p1_matches=self._historical_p1_matches(user.id, error_templates),
        ))
        error_ts = [aware(e[4]) for e in entries if e[1] in ("ERROR", "CRITICAL") and e[4] is not None]
        start, end = aware(cand.start), aware(cand.end)
        now = datetime.now(UTC)
        incident = Incident(
            user_id=user.id, upload_id=upload.id, fingerprint=fp,
            title=f"Anomalous activity in {cand.primary_service}",
            description=(f"{stats.error_count} error events ({stats.critical_count} critical) among {stats.total_events} log events "
                         f"between {start.isoformat()} and {end.isoformat()} in {upload.filename}. Detected by {method} "
                         f"(max score {cand.max_score} vs threshold {first.threshold}; the score is not a probability)."),
            service=cand.primary_service, severity=severity.severity, status="OPEN",
            severity_reasons=severity.reasons, services=cand.services, templates=templates, error_templates=error_templates,
            anomaly_summary={**self._summary(cand, method), "rca": self._rca(user.id, upload.id, start, end)},
            detection_time=aware(first.detection_timestamp) or now,
            first_occurrence=min(error_ts) if error_ts else start, last_occurrence=max(error_ts) if error_ts else end,
        )
        self.db.add(incident)
        self.db.flush()
        self._event(incident.id, "ABNORMAL_ACTIVITY", start, "First abnormal window (statistical anomaly in log activity)",
                    None, {"window_start": start.isoformat()})
        if error_ts:
            self._event(incident.id, "FIRST_ERROR", min(error_ts), "First error-level log event in the affected range")
        self._event(incident.id, "ANOMALY_DETECTED", aware(first.detection_timestamp) or now, f"Anomaly detected by {method}",
                    None, {"max_score": cand.max_score, "threshold": first.threshold})
        self._event(incident.id, "INCIDENT_CREATED", now, f"Incident created automatically with severity {severity.severity}",
                    user.id, {"severity": severity.severity, "reasons": severity.reasons})
        for entry in [e for e in entries if e[1] in ("ERROR", "CRITICAL")][:MAX_LINKED_LOGS]:
            self.db.add(IncidentLogLink(incident_id=incident.id, log_entry_id=entry[0]))
        return incident

    def _refresh(self, incident: Incident, cand: IncidentCandidate, entries: list[tuple], method: str) -> bool:
        """Extend an existing incident. Severity, status and title are never overwritten automatically."""
        start, end = aware(cand.start), aware(cand.end)
        error_ts = [aware(e[4]) for e in entries if e[1] in ("ERROR", "CRITICAL") and e[4] is not None]
        new_first = min([t for t in [aware(incident.first_occurrence), start, *error_ts] if t])
        new_last = max([t for t in [aware(incident.last_occurrence), end, *error_ts] if t])
        extended = new_first != aware(incident.first_occurrence) or new_last != aware(incident.last_occurrence)
        incident.first_occurrence, incident.last_occurrence = new_first, new_last
        incident.anomaly_summary = {**self._summary(cand, method), "rca": self._rca(incident.user_id, incident.upload_id, new_first, new_last + timedelta(seconds=1))}  # type: ignore[arg-type]
        have = set(self.db.scalars(select(IncidentLogLink.log_entry_id).where(IncidentLogLink.incident_id == incident.id)))
        room = MAX_LINKED_LOGS - len(have)
        for entry in [e for e in entries if e[1] in ("ERROR", "CRITICAL") and e[0] not in have][:max(room, 0)]:
            self.db.add(IncidentLogLink(incident_id=incident.id, log_entry_id=entry[0]))
        if extended:
            self._event(incident.id, "ANOMALY_UPDATED", datetime.now(UTC), "Additional anomalous activity merged into this incident")
        return extended
