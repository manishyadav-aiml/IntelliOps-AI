from pathlib import Path

import numpy as np
import pytest

from app.rag.embeddings import EmbeddingUnavailableError, HashingEmbedder, create_embedder
from app.rag.vector_store import VectorStore, VectorStoreError


def cos(a, b) -> float:
    return float(np.dot(a, b))


def test_similar_messages_score_higher_than_different_ones() -> None:
    e = HashingEmbedder()
    v = e.embed([
        "payment service gateway timeout database connection refused",
        "payment gateway timeout while connecting to database",
        "user logged in successfully from mobile app",
    ])
    assert cos(v[0], v[1]) > cos(v[0], v[2]) + 0.2
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-5)


def test_empty_input_is_handled() -> None:
    e = HashingEmbedder()
    assert e.embed([]).shape == (0, e.dim)
    assert not np.any(e.embed([""])[0])  # zero vector, never NaN


def test_missing_embedding_model_falls_back_or_raises() -> None:
    fallback = create_embedder("definitely/not-a-real-model")
    assert fallback.name == "hashing-lexical" and fallback.fallback_reason
    with pytest.raises(EmbeddingUnavailableError):
        create_embedder("definitely/not-a-real-model", allow_fallback=False)
    assert create_embedder("hashing").fallback_reason is None


def build_store() -> tuple[VectorStore, HashingEmbedder]:
    e = HashingEmbedder()
    texts = ["db timeout payment", "login failed auth", "disk full memory warning"]
    store = VectorStore(e.dim, e.name)
    store.add(
        ["a", "b", "c"], e.embed(texts),
        [{"owner_id": 1, "t": "x"}, {"owner_id": 1, "t": "y"}, {"owner_id": 2, "t": "z"}],
    )
    return store, e


def test_search_ranks_threshold_and_exclude() -> None:
    store, e = build_store()
    hits = store.search(e.embed(["db timeout payment error"])[0], k=3)
    assert hits[0].id == "a"
    assert store.search(e.embed(["db timeout payment error"])[0], threshold=0.99) == []
    assert "a" not in [h.id for h in store.search(e.embed(["db timeout"])[0], exclude_ids={"a"})]


def test_search_enforces_owner_isolation() -> None:
    store, e = build_store()
    q = e.embed(["disk full memory warning"])[0]
    assert store.search(q, owner_id=1, threshold=0.3) == []  # item "c" belongs to owner 2
    assert [h.id for h in store.search(q, owner_id=2, threshold=0.3)] == ["c"]


def test_empty_query_and_empty_store_return_nothing() -> None:
    store, e = build_store()
    assert store.search(e.embed([""])[0]) == []
    assert VectorStore(e.dim).search(e.embed(["x"])[0]) == []


def test_remove_upsert_and_dimension_checks() -> None:
    store, e = build_store()
    assert store.remove(["a", "nope"]) == 1 and len(store) == 2
    store.add(["b"], e.embed(["replaced text"]), [{"owner_id": 1}])  # upsert
    assert len(store) == 2 and store.meta[store.ids.index("b")] == {"owner_id": 1}
    with pytest.raises(VectorStoreError):
        store.add(["z"], np.ones((1, 3), dtype=np.float32), [{}])


def test_persistence_roundtrip_keeps_metadata_in_a_separate_file(tmp_path: Path) -> None:
    store, e = build_store()
    store.save(tmp_path)
    assert (tmp_path / "vectors.npy").exists() and (tmp_path / "metadata.json").exists()
    loaded = VectorStore.load(tmp_path, e.dim, e.name)
    q = e.embed(["db timeout payment"])[0]
    assert [h.id for h in loaded.search(q, k=2)] == [h.id for h in store.search(q, k=2)]


def test_stale_or_missing_index_requires_rebuild(tmp_path: Path) -> None:
    store, e = build_store()
    store.save(tmp_path)
    with pytest.raises(VectorStoreError):
        VectorStore.load(tmp_path, e.dim, "other-embedder")
    with pytest.raises(VectorStoreError):
        VectorStore.load(tmp_path / "missing", e.dim, e.name)


def test_rebuild_replaces_contents() -> None:
    store, e = build_store()
    store.rebuild(["n"], e.embed(["new thing"]), [{"owner_id": 1}])
    assert store.ids == ["n"]


def test_faiss_request_falls_back_to_numpy_when_missing() -> None:
    store = VectorStore(8, "x", backend="faiss")
    assert store.backend in {"faiss", "numpy"}


# ---------- lexical fallback quality (regression tests for bugs found by simulation) ----------
def test_analyzer_drops_stopwords_stems_and_normalises_timeout() -> None:
    from app.rag.embeddings import analyze

    tokens = analyze("What should I check when payments time out?")
    assert {"check", "payment", "timeout"} <= set(tokens) and "what" not in tokens and "when" not in tokens
    assert analyze("Connection timeouts") == analyze("connection time-outs")


def test_unrelated_texts_do_not_look_similar_and_related_ones_do() -> None:
    from app.services.similarity import incident_text

    e = HashingEmbedder()

    def vec(title: str, service: str):
        return e.embed([incident_text(title, service, "P2", [], ["Severity set manually by someone"])])[0]

    a, b, other = vec("Payment gateway timeout errors", "payment-service"), vec("Payment gateway timeout again", "payment-service"), vec("Disk almost full on storage node", "storage")
    assert cos(a, b) > 0.5 and cos(a, other) < 0.1
