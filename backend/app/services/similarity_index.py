"""Per-user incident similarity index (persisted, rebuildable). Similarity is not a root-cause proof."""

from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.incident import Incident, IncidentRelationship
from app.rag.vector_store import VectorStore, VectorStoreError
from app.services.embedder_cache import get_embedder
from app.services.incident_logic import incident_public_id, parse_public_id
from app.services.similarity import SimilarIncident, find_similar, incident_text, index_metadata


class SimilarityIndexService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.embedder = get_embedder(settings)

    def _dir(self, user_id: int) -> Path:
        return Path(self.settings.index_dir) / f"user_{user_id}" / "incidents"

    @staticmethod
    def _text(incident: Incident) -> str:
        return incident_text(incident.title, incident.service, incident.severity, incident.templates, incident.severity_reasons)

    def _meta(self, incident: Incident) -> dict:
        return index_metadata(incident.user_id, incident_public_id(incident.id), incident.title,
                              incident.services or [incident.service], incident.templates, incident.error_templates)

    def store(self, user_id: int) -> VectorStore:
        try:
            return VectorStore.load(self._dir(user_id), self.embedder.dim, self.embedder.name, self.settings.matcher)
        except VectorStoreError:
            return self.rebuild(user_id)

    def rebuild(self, user_id: int) -> VectorStore:
        incidents = list(self.db.scalars(select(Incident).where(Incident.user_id == user_id)))
        store = VectorStore(self.embedder.dim, self.embedder.name, self.settings.matcher)
        if incidents:
            store.add([incident_public_id(i.id) for i in incidents], self.embedder.embed([self._text(i) for i in incidents]),
                      [self._meta(i) for i in incidents])
        store.save(self._dir(user_id))
        return store

    def upsert(self, incident: Incident) -> None:
        store = self.store(incident.user_id)
        store.add([incident_public_id(incident.id)], self.embedder.embed([self._text(incident)]), [self._meta(incident)])
        store.save(self._dir(incident.user_id))

    def similar(self, incident: Incident, k: int = 5) -> list[SimilarIncident]:
        store = self.store(incident.user_id)
        meta = self._meta(incident)
        return find_similar(store, self.embedder, incident.user_id, meta["incident_id"], self._text(incident),
                            meta["services"], incident.templates, incident.error_templates, k, self.settings.similarity_min_score)

    def refresh_relationships(self, incident: Incident) -> list[SimilarIncident]:
        """Persist links to similar incidents of the SAME user (replacing earlier links)."""
        hits = self.similar(incident)
        self.db.execute(delete(IncidentRelationship).where(IncidentRelationship.incident_id == incident.id))
        for hit in hits:
            other = parse_public_id(hit.similar_incident_id)
            if other is None:
                continue
            self.db.add(IncidentRelationship(
                incident_id=incident.id, related_incident_id=other, similarity_score=hit.similarity_score,
                shared={"services": hit.shared_services, "templates": hit.shared_templates, "error_patterns": hit.shared_error_patterns},
            ))
        return hits
