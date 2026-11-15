"""Text embeddings behind one interface.

* SentenceTransformerEmbedder - semantic embeddings (needs `sentence-transformers` and the model files).
* HashingEmbedder             - dependency-light LEXICAL fallback (word/bigram hashing). It matches
                                shared wording, not meaning; documented as a degraded mode.
"""

from typing import Protocol

import re

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

HASHING_DIM = 4096  # collisions grow as this shrinks; 4096 floats = 16 KB per vector

# Lexical analysis for the fallback embedder: without it, common words ("what", "is", "the") dominate the
# vectors and unrelated texts look similar, while "payments" would not match "payment".
STOPWORDS = frozenset(
    "a an and are as at be but by can could did do does for from had has have how i if in into is it its me my no not "
    "of on or our should so than that the their then there these they this to up us was we were what when where which "
    "who why will with would you your about after again all also any been before being between both during each few "
    "more most other over same some such too very while".split()
)
_TOKEN = re.compile(r"[a-z0-9]+")
_PHRASES = ((re.compile(r"\btime[\s-]+out(s?)\b"), r"timeout\1"), (re.compile(r"\bsign[\s-]+in\b"), "signin"),
            (re.compile(r"\blog[\s-]+in\b"), "login"))


def _stem(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def analyze(text: str) -> list[str]:
    """Lowercase, normalise a few phrases, drop stopwords and bare numbers, stem lightly; unigrams + bigrams."""
    text = text.lower()
    for pattern, replacement in _PHRASES:
        text = pattern.sub(replacement, text)
    tokens = [_stem(t) for t in _TOKEN.findall(text) if t not in STOPWORDS and not t.isdigit()]
    return tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False)]


class EmbeddingUnavailableError(RuntimeError):
    """The requested embedding model cannot be loaded."""


class Embedder(Protocol):
    name: str
    dim: int
    fallback_reason: str | None

    def embed(self, texts: list[str]) -> np.ndarray: ...


class HashingEmbedder:
    name = "hashing-lexical"
    dim = HASHING_DIM

    def __init__(self, fallback_reason: str | None = None) -> None:
        self.fallback_reason = fallback_reason
        self._vectorizer = HashingVectorizer(n_features=HASHING_DIM, alternate_sign=False, norm="l2", analyzer=analyze)

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return self._vectorizer.transform(texts).toarray().astype(np.float32)


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(model_name)
        except Exception as exc:  # ImportError, missing/offline model, etc.
            raise EmbeddingUnavailableError(f"Embedding model '{model_name}' is unavailable: {type(exc).__name__}") from exc
        self.name = model_name
        self.dim = int(self._model.get_sentence_embedding_dimension())
        self.fallback_reason = None

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.asarray(self._model.encode(texts, normalize_embeddings=True), dtype=np.float32)


def create_embedder(model_name: str, allow_fallback: bool = True) -> Embedder:
    """`model_name` in ("", "hashing") selects the lexical embedder explicitly."""
    if model_name in ("", "hashing", "hashing-lexical"):
        return HashingEmbedder()
    try:
        return SentenceTransformerEmbedder(model_name)
    except EmbeddingUnavailableError as exc:
        if not allow_fallback:
            raise
        return HashingEmbedder(fallback_reason=str(exc))
