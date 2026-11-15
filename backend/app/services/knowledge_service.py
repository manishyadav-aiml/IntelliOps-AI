"""Documentation library + RAG: per-user document index, background indexing, grounded Q&A."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.orm import Session

from app.ai.llm_provider import LLMProvider
from app.core.config import Settings
from app.core.exceptions import InvalidStateError, NotFoundError
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.rag.chunking import Chunk, chunk_pages
from app.rag.document_loader import InvalidDocumentError, load_document
from app.rag.embeddings import EmbeddingUnavailableError
from app.rag.generator import RagAnswer, answer_question
from app.rag.retrieval import index_document, remove_document, retrieve
from app.rag.vector_store import VectorStore, VectorStoreError
from app.repositories.audit_repository import AuditRepository
from app.schemas.knowledge import CitationRead, DocumentRead, RagResponse
from app.schemas.log import Page
from app.services.embedder_cache import get_embedder

logger = logging.getLogger(__name__)


class DocumentIndexService:
    """One persisted vector store per user. Chunk text lives in the DB; vectors can always be rebuilt."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self.db, self.settings = db, settings
        self.embedder = get_embedder(settings)

    def _dir(self, user_id: int) -> Path:
        return Path(self.settings.index_dir) / f"user_{user_id}" / "documents"

    def store(self, user_id: int) -> VectorStore:
        try:
            return VectorStore.load(self._dir(user_id), self.embedder.dim, self.embedder.name, self.settings.matcher)
        except VectorStoreError:
            return self.rebuild(user_id)

    def rebuild(self, user_id: int) -> VectorStore:
        store = VectorStore(self.embedder.dim, self.embedder.name, self.settings.matcher)
        docs = self.db.scalars(select(Document).where(Document.user_id == user_id, Document.status == "COMPLETED")).all()
        for doc in docs:
            chunks = self.db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index)).all()
            index_document(store, self.embedder, user_id, doc.id, doc.filename,
                           [Chunk(c.chunk_id, c.chunk_index, c.page_number, c.text) for c in chunks])
        store.save(self._dir(user_id))
        return store

    def index(self, doc: Document, chunks: list[Chunk]) -> int:
        store = self.store(doc.user_id)
        count = index_document(store, self.embedder, doc.user_id, doc.id, doc.filename, chunks)
        store.save(self._dir(doc.user_id))
        return count

    def remove(self, user_id: int, document_id: int) -> None:
        store = self.store(user_id)
        remove_document(store, document_id)
        store.save(self._dir(user_id))


class DocumentService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db, self.settings = db, settings
        self.audit = AuditRepository(db)
        self.index = DocumentIndexService(db, settings)

    def user_directory(self, user: User) -> Path:
        return Path(self.settings.upload_dir) / "documents" / str(user.id)

    def register(self, user: User, stored: Path, size: int, name: str, ip: str | None) -> Document:
        doc = Document(user_id=user.id, filename=name, stored_path=f"documents/{user.id}/{stored.name}",
                       extension=stored.suffix.lower(), size_bytes=size, status="PENDING")
        try:
            self.db.add(doc)
            self.db.flush()
            self.audit.record("document.uploaded", user.id, ip, "document", str(doc.id))
            self.db.commit()
        except Exception:
            self.db.rollback()
            stored.unlink(missing_ok=True)
            raise
        return doc

    def get(self, user: User, doc_id: int) -> Document:
        doc = self.db.scalar(select(Document).where(Document.id == doc_id, Document.user_id == user.id))
        if doc is None:
            raise NotFoundError("Document not found")
        return doc

    def list_documents(self, user: User, page: int, page_size: int, status: str | None, q: str | None) -> Page[DocumentRead]:
        stmt = select(Document).where(Document.user_id == user.id)
        if status:
            stmt = stmt.where(Document.status == status)
        if q:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(Document.filename.ilike(f"%{escaped}%", escape="\\"))
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = self.db.scalars(stmt.order_by(Document.created_at.desc(), Document.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return Page(items=[DocumentRead.model_validate(r) for r in rows], total=total, page=page, page_size=page_size)

    def request_index(self, user: User, doc_id: int, ip: str | None) -> Document:
        """Re-queue indexing (retry after FAILED, or re-embed after changing the embedding model)."""
        doc = self.get(user, doc_id)
        if doc.status == "PROCESSING":
            raise InvalidStateError("The document is already being indexed")
        if doc.status in ("FAILED", "COMPLETED"):
            doc.status, doc.error_message = "PENDING", None
            self.audit.record("document.reindex_requested", user.id, ip, "document", str(doc.id))
            self.db.commit()
        return doc

    def delete(self, user: User, doc_id: int, ip: str | None) -> None:
        doc = self.get(user, doc_id)
        if doc.status == "PROCESSING":
            raise InvalidStateError("Cannot delete a document while it is being indexed")
        path = Path(self.settings.upload_dir) / doc.stored_path
        self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        self.db.delete(doc)
        self.audit.record("document.deleted", user.id, ip, "document", str(doc_id))
        self.db.commit()
        self.index.remove(user.id, doc_id)  # vectors disappear from retrieval immediately
        path.unlink(missing_ok=True)


class DocumentProcessor:
    """Background indexing with its own DB session: PENDING -> PROCESSING -> COMPLETED | FAILED."""

    def __init__(self, session_factory: Callable[[], Session], settings: Settings) -> None:
        self.session_factory, self.settings = session_factory, settings

    def process(self, doc_id: int) -> None:
        with self.session_factory() as db:
            claimed = db.execute(update(Document).where(Document.id == doc_id, Document.status == "PENDING")
                                 .values(status="PROCESSING", started_at=datetime.now(UTC), error_message=None))
            db.commit()
            if claimed.rowcount != 1:
                return
            try:
                self._run(db, doc_id)
            except InvalidDocumentError as exc:
                self._fail(db, doc_id, exc.message)
            except EmbeddingUnavailableError as exc:
                self._fail(db, doc_id, str(exc))
            except Exception as exc:
                logger.exception("Indexing failed for document %s", doc_id)
                self._fail(db, doc_id, f"Indexing failed ({type(exc).__name__}). You can retry.")

    def _fail(self, db: Session, doc_id: int, message: str) -> None:
        db.rollback()
        doc = db.get(Document, doc_id)
        if doc:
            doc.status, doc.error_message, doc.completed_at = "FAILED", message[:500], datetime.now(UTC)
            db.commit()

    def _run(self, db: Session, doc_id: int) -> None:
        doc = db.get(Document, doc_id)
        assert doc is not None
        pages = load_document(Path(self.settings.upload_dir) / doc.stored_path)
        chunks = chunk_pages(pages, self.settings.rag_chunk_size, self.settings.rag_chunk_overlap)
        if not chunks:
            raise InvalidDocumentError("No text could be split into chunks")
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        db.execute(insert(DocumentChunk), [
            {"document_id": doc.id, "user_id": doc.user_id, "chunk_id": c.chunk_id, "chunk_index": c.index,
             "page_number": c.page_number, "text": c.text} for c in chunks
        ])
        service = DocumentIndexService(db, self.settings)
        service.index(doc, chunks)
        doc.page_count, doc.chunk_count = len(pages), len(chunks)
        doc.embedder_name = service.embedder.name
        doc.status, doc.completed_at = "COMPLETED", datetime.now(UTC)
        db.commit()


class RagService:
    def __init__(self, db: Session, settings: Settings, provider: LLMProvider | None) -> None:
        self.db, self.settings, self.provider = db, settings, provider
        self.index = DocumentIndexService(db, settings)

    def query(self, user: User, question: str, document_ids: list[int] | None, ip: str | None) -> RagResponse:
        allowed: set[int] | None = None
        if document_ids:
            allowed = set(self.db.scalars(select(Document.id).where(Document.user_id == user.id, Document.id.in_(document_ids))))
        chunks = retrieve(self.index.store(user.id), self.index.embedder, user.id, question,
                          self.settings.rag_top_k, self.settings.rag_similarity_threshold, allowed)
        answer: RagAnswer = answer_question(question, chunks, self.provider)
        AuditRepository(self.db).record("rag.query", user.id, ip, details={"question_length": len(question), "chunks": len(chunks)})
        self.db.commit()
        return RagResponse(
            answer=answer.answer, sufficient=answer.sufficient, llm_used=answer.llm_used, notice=answer.notice,
            citations=[CitationRead(**c.__dict__) for c in answer.citations],
        )
