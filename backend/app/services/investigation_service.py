"""AI incident investigation: gather real evidence, ask the LLM (if configured), validate, store."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.investigation_agent import InvestigationAgent, build_evidence
from app.ai.llm_provider import LLMProvider
from app.core.config import Settings
from app.core.exceptions import AIUnavailableError
from app.models.incident import AIInvestigation, IncidentEvent, IncidentLogLink, IncidentNote
from app.models.log import LogEntry
from app.models.user import User
from app.rag.retrieval import retrieve
from app.repositories.audit_repository import AuditRepository
from app.services.incident_service import IncidentService
from app.services.knowledge_service import DocumentIndexService


class InvestigationService:
    def __init__(self, db: Session, settings: Settings, provider: LLMProvider | None) -> None:
        self.db, self.settings, self.provider = db, settings, provider
        self.incidents = IncidentService(db, settings)
        self.documents = DocumentIndexService(db, settings)

    def investigate(self, user: User, incident_id: int, question: str | None, ip: str | None) -> AIInvestigation:
        incident = self.incidents.get(user, incident_id)
        question = (question or "").strip() or f"Why is the {incident.service} service failing?"

        log_rows = self.db.execute(
            select(LogEntry.timestamp, LogEntry.level, LogEntry.service, LogEntry.message)
            .join(IncidentLogLink, IncidentLogLink.log_entry_id == LogEntry.id)
            .where(IncidentLogLink.incident_id == incident.id, LogEntry.user_id == user.id)
            .order_by(LogEntry.timestamp).limit(15)
        ).all()
        logs = [{"timestamp": str(t), "level": lv, "service": s, "message": m} for t, lv, s, m in log_rows]
        similar = self.incidents.similar(user, incident_id)
        docs = retrieve(self.documents.store(user.id), self.documents.embedder, user.id, f"{incident.title} {question}",
                        3, self.settings.rag_similarity_threshold)
        notes = [n for n in self.db.scalars(select(IncidentNote.content).where(IncidentNote.incident_id == incident.id)
                                            .order_by(IncidentNote.created_at).limit(10))]
        evidence = build_evidence(
            logs, [{"template_text": t} for t in (incident.templates or [])[:8]], incident.anomaly_summary,
            {"severity": incident.severity, "reasons": incident.severity_reasons or []},
            [{"incident_id": s.similar_incident_id, "score": s.similarity_score, "title": s.title or ""} for s in similar],
            [{"document": d.document_name, "page": d.page_number, "text": d.text} for d in docs],
            [f"Engineer note: {n}" for n in notes],
            (incident.anomaly_summary or {}).get("rca"),
        )
        agent = InvestigationAgent(self.provider)
        outcome = agent.investigate(question, incident.description, evidence, {s.similar_incident_id for s in similar})

        provider_name = getattr(self.provider, "name", "none")
        record = AIInvestigation(
            incident_id=incident.id, user_id=user.id, question=question, provider=provider_name,
            status="COMPLETED" if outcome.ok else "FAILED",
            result=outcome.investigation.to_dict() if outcome.investigation else None,
            error_code=outcome.error_code, error_message=outcome.error_message,
        )
        self.db.add(record)
        self.db.add(IncidentEvent(
            incident_id=incident.id, event_type="AI_INVESTIGATION", timestamp=datetime.now(UTC), actor_user_id=user.id,
            description="AI investigation run (suggestions only, not confirmed)" if outcome.ok else f"AI investigation failed: {outcome.error_code}",
        ))
        AuditRepository(self.db).record("incident.investigated", user.id, ip, "incident", str(incident.id),
                                        {"ok": outcome.ok, "error_code": outcome.error_code})
        self.db.commit()
        if not outcome.ok:
            raise AIUnavailableError(outcome.error_code or "ai_unavailable", outcome.error_message or "The AI service failed.")
        return record
