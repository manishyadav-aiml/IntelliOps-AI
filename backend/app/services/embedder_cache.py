"""Process-wide embedder cache (loading a sentence-transformer is slow and memory hungry)."""

from threading import Lock

from app.core.config import Settings
from app.rag.embeddings import Embedder, create_embedder

_cache: dict[tuple[str, bool], Embedder] = {}
_lock = Lock()


def get_embedder(settings: Settings) -> Embedder:
    key = (settings.embedding_model, settings.embedding_fallback)
    with _lock:
        if key not in _cache:
            _cache[key] = create_embedder(settings.embedding_model, settings.embedding_fallback)
        return _cache[key]
