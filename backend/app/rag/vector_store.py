"""Cosine-similarity vector store with metadata kept separate from vectors.

Uses FAISS (IndexFlatIP over L2-normalised vectors) when available and requested, otherwise an exact
NumPy search. Both return the same results; FAISS only matters for large indexes.

Isolation: every item carries `owner_id` in its metadata and `search()` can enforce it. Callers also
keep one store per user, so cross-user retrieval is blocked twice.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


class VectorStoreError(RuntimeError):
    pass


@dataclass
class SearchHit:
    id: str
    score: float
    metadata: dict[str, Any]


class VectorStore:
    def __init__(self, dim: int, embedder_name: str = "", backend: str = "numpy") -> None:
        self.dim = dim
        self.embedder_name = embedder_name
        self.ids: list[str] = []
        self.meta: list[dict[str, Any]] = []
        self.vectors = np.zeros((0, dim), dtype=np.float32)
        self._faiss: Any = None
        self._faiss_dirty = True
        self.backend = "numpy"
        if backend == "faiss":
            try:
                import faiss  # noqa: F401

                self.backend = "faiss"
            except ImportError:
                self.backend = "numpy"  # documented fallback

    def __len__(self) -> int:
        return len(self.ids)

    def add(self, ids: list[str], vectors: np.ndarray, metadata: list[dict[str, Any]]) -> None:
        if not (len(ids) == len(vectors) == len(metadata)):
            raise VectorStoreError("ids, vectors and metadata must have the same length")
        if len(ids) == 0:
            return
        if vectors.shape[1] != self.dim:
            raise VectorStoreError(f"Vector dimension {vectors.shape[1]} does not match index dimension {self.dim}")
        existing = set(ids) & set(self.ids)
        if existing:
            self.remove(list(existing))  # upsert
        self.ids.extend(ids)
        self.meta.extend(metadata)
        self.vectors = np.vstack([self.vectors, vectors.astype(np.float32)])
        self._faiss_dirty = True

    def remove(self, ids: list[str]) -> int:
        drop = set(ids)
        keep = [i for i, item in enumerate(self.ids) if item not in drop]
        removed = len(self.ids) - len(keep)
        if removed:
            self.ids = [self.ids[i] for i in keep]
            self.meta = [self.meta[i] for i in keep]
            self.vectors = self.vectors[keep] if keep else np.zeros((0, self.dim), dtype=np.float32)
            self._faiss_dirty = True
        return removed

    def rebuild(self, ids: list[str], vectors: np.ndarray, metadata: list[dict[str, Any]]) -> None:
        self.ids, self.meta = [], []
        self.vectors = np.zeros((0, self.dim), dtype=np.float32)
        self._faiss_dirty = True
        self.add(ids, vectors, metadata)

    def _scores(self, query: np.ndarray) -> np.ndarray:
        if self.backend == "faiss":
            import faiss

            if self._faiss_dirty or self._faiss is None:
                self._faiss = faiss.IndexFlatIP(self.dim)
                if len(self.ids):
                    self._faiss.add(self.vectors)
                self._faiss_dirty = False
            scores, idx = self._faiss.search(query.reshape(1, -1).astype(np.float32), len(self.ids))
            out = np.full(len(self.ids), -1.0, dtype=np.float32)
            out[idx[0][idx[0] >= 0]] = scores[0][idx[0] >= 0]
            return out
        return self.vectors @ query.astype(np.float32)

    def search(
        self, query: np.ndarray, k: int = 5, threshold: float | None = None, owner_id: int | None = None,
        exclude_ids: set[str] | None = None,
    ) -> list[SearchHit]:
        if len(self.ids) == 0 or not np.any(query):
            return []
        if query.shape[-1] != self.dim:
            raise VectorStoreError("Query dimension does not match the index")
        scores = self._scores(query.reshape(-1))
        hits: list[SearchHit] = []
        for i in np.argsort(-scores):
            if owner_id is not None and self.meta[i].get("owner_id") != owner_id:
                continue
            if exclude_ids and self.ids[i] in exclude_ids:
                continue
            score = float(scores[i])
            if threshold is not None and score < threshold:
                break
            hits.append(SearchHit(self.ids[i], round(score, 6), self.meta[i]))
            if len(hits) >= k:
                break
        return hits

    # ---- persistence: vectors and metadata are stored in separate files ----
    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / "vectors.npy", self.vectors)
        (directory / "metadata.json").write_text(
            json.dumps({"dim": self.dim, "embedder": self.embedder_name, "ids": self.ids, "meta": self.meta})
        )

    @classmethod
    def load(cls, directory: Path, dim: int, embedder_name: str, backend: str = "numpy") -> "VectorStore":
        try:
            vectors = np.load(directory / "vectors.npy")
            payload = json.loads((directory / "metadata.json").read_text())
        except (OSError, ValueError) as exc:
            raise VectorStoreError("Index files are missing or unreadable; rebuild the index") from exc
        if payload["dim"] != dim or payload["embedder"] != embedder_name or len(payload["ids"]) != len(vectors):
            raise VectorStoreError("Index was built with a different embedder/dimension; rebuild the index")
        store = cls(dim, embedder_name, backend)
        store.ids, store.meta, store.vectors = payload["ids"], payload["meta"], vectors.astype(np.float32)
        return store
