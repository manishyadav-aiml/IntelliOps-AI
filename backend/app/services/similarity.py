"""Similar-incident retrieval. Similarity is NOT evidence of a common root cause."""

from dataclasses import dataclass, field

import numpy as np

from app.rag.embeddings import Embedder
from app.rag.vector_store import VectorStore


def incident_text(title: str, service: str, severity: str, templates: list[str], reasons: list[str]) -> str:
    """The text that represents an incident in the vector index.

    Only content that characterises the problem is used (title, service, log templates). Severity and its
    boilerplate reasons are deliberately left out: they are shared by most incidents and would make unrelated
    incidents look alike. `severity` and `reasons` stay in the signature for callers.
    """
    parts = [title, service, *templates[:15]]
    return "\n".join(p for p in parts if p and p != "unknown")


def shared(a: list[str], b: list[str]) -> list[str]:
    other = set(b)
    seen: list[str] = []
    for item in a:
        if item in other and item not in seen:
            seen.append(item)
    return seen


@dataclass
class SimilarIncident:
    incident_id: str
    similar_incident_id: str
    similarity_score: float
    shared_services: list[str] = field(default_factory=list)
    shared_templates: list[str] = field(default_factory=list)
    shared_error_patterns: list[str] = field(default_factory=list)
    note: str = "Similarity indicates comparable symptoms, not a confirmed common root cause."


def index_metadata(owner_id: int, incident_id: str, title: str, services: list[str], templates: list[str],
                   error_templates: list[str]) -> dict:
    return {
        "owner_id": owner_id, "incident_id": incident_id, "title": title,
        "services": services, "templates": templates, "error_templates": error_templates,
    }


def find_similar(
    store: VectorStore, embedder: Embedder, owner_id: int, incident_id: str, query_text: str,
    services: list[str], templates: list[str], error_templates: list[str], k: int = 5, min_score: float = 0.3,
) -> list[SimilarIncident]:
    if not query_text.strip() or len(store) == 0:
        return []
    vector: np.ndarray = embedder.embed([query_text])[0]
    hits = store.search(vector, k=k, threshold=min_score, owner_id=owner_id, exclude_ids={incident_id})
    return [
        SimilarIncident(
            incident_id=incident_id,
            similar_incident_id=hit.id,
            similarity_score=hit.score,
            shared_services=shared(services, hit.metadata.get("services", [])),
            shared_templates=shared(templates, hit.metadata.get("templates", [])),
            shared_error_patterns=shared(error_templates, hit.metadata.get("error_templates", [])),
        )
        for hit in hits
    ]
