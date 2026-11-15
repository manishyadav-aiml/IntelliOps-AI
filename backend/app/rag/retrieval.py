"""Indexing and retrieval of document chunks. One vector store per user + owner filter on search."""

from dataclasses import dataclass

from app.rag.chunking import Chunk
from app.rag.embeddings import Embedder
from app.rag.vector_store import VectorStore


@dataclass
class RetrievedChunk:
    ref: str  # "<document_id>:<chunk_id>" - a real, stored chunk
    document_id: int
    document_name: str
    page_number: int | None
    chunk_id: str
    text: str
    score: float


def index_document(store: VectorStore, embedder: Embedder, owner_id: int, document_id: int,
                   document_name: str, chunks: list[Chunk]) -> int:
    """(Re)index one document. Existing chunks of the same document are replaced."""
    remove_document(store, document_id)
    if not chunks:
        return 0
    vectors = embedder.embed([c.text for c in chunks])
    store.add(
        [f"{document_id}:{c.chunk_id}" for c in chunks],
        vectors,
        [{"owner_id": owner_id, "document_id": document_id, "document_name": document_name,
          "page_number": c.page_number, "chunk_id": c.chunk_id, "text": c.text} for c in chunks],
    )
    return len(chunks)


def remove_document(store: VectorStore, document_id: int) -> int:
    prefix = f"{document_id}:"
    return store.remove([i for i in store.ids if i.startswith(prefix)])


def retrieve(store: VectorStore, embedder: Embedder, owner_id: int, query: str, top_k: int = 4,
             min_score: float = 0.15, document_ids: set[int] | None = None) -> list[RetrievedChunk]:
    if not query.strip() or len(store) == 0:
        return []
    vector = embedder.embed([query])[0]
    hits = store.search(vector, k=max(top_k * 5, top_k) if document_ids else top_k, threshold=min_score, owner_id=owner_id)
    out = []
    for hit in hits:
        if document_ids and hit.metadata["document_id"] not in document_ids:
            continue
        m = hit.metadata
        out.append(RetrievedChunk(hit.id, m["document_id"], m["document_name"], m["page_number"], m["chunk_id"], m["text"], hit.score))
        if len(out) >= top_k:
            break
    return out
