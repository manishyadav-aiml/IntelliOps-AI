"""Document validation and text extraction (PDF, TXT, Markdown). Documents are untrusted input."""

import codecs
from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import AppError

ALLOWED_DOC_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}
MAX_PDF_PAGES = 500
MAX_TEXT_CHARS = 5_000_000


class InvalidDocumentError(AppError):
    status_code = 422
    code = "invalid_document"


@dataclass
class PageText:
    page_number: int | None  # None for plain text / markdown
    text: str


def document_extension(filename: str | None) -> str:
    ext = Path((filename or "").replace("\\", "/").split("/")[-1]).suffix.lower()
    if ext not in ALLOWED_DOC_EXTENSIONS:
        raise InvalidDocumentError("Only PDF, TXT and Markdown documents are supported")
    return ext


def validate_document_head(head: bytes, extension: str) -> None:
    """Content check on the first bytes (the extension alone is never trusted)."""
    if not head.strip():
        raise InvalidDocumentError("The document is empty")
    if extension == ".pdf":
        if not head.lstrip().startswith(b"%PDF"):
            raise InvalidDocumentError("The file is not a valid PDF")
        return
    if head.startswith((b"MZ", b"\x7fELF", b"PK\x03\x04", b"%PDF", b"#!")) or b"\x00" in head:
        raise InvalidDocumentError("The file does not look like a text document")
    text = codecs.getincrementaldecoder("utf-8")(errors="replace").decode(head, final=False)
    if text.count("\ufffd") / max(len(text), 1) > 0.10:
        raise InvalidDocumentError("The document is not valid UTF-8 text")


def load_document(path: Path) -> list[PageText]:
    ext = path.suffix.lower()
    pages = _load_pdf(path) if ext == ".pdf" else _load_text(path)
    if not any(p.text.strip() for p in pages):
        raise InvalidDocumentError("No extractable text found (is this a scanned document?)")
    return pages


def _load_text(path: Path) -> list[PageText]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")[:MAX_TEXT_CHARS]
    return [PageText(None, text)]


def _load_pdf(path: Path) -> list[PageText]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise InvalidDocumentError("Encrypted PDFs are not supported")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise InvalidDocumentError(f"PDF has more than {MAX_PDF_PAGES} pages")
        return [PageText(i + 1, (page.extract_text() or "")) for i, page in enumerate(reader.pages)]
    except InvalidDocumentError:
        raise
    except Exception as exc:  # corrupt or unreadable PDF
        raise InvalidDocumentError("The PDF could not be read") from exc
