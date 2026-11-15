"""Safe streaming storage for documentation uploads (PDF / TXT / Markdown)."""

import uuid
from pathlib import Path

from app.rag.document_loader import InvalidDocumentError, document_extension, validate_document_head
from app.services.log_upload import SAMPLE_BYTES, AsyncReadable, FileTooLargeError, sanitize_filename

CHUNK = 1024 * 1024


async def save_document(file: AsyncReadable, directory: Path, max_bytes: int) -> tuple[Path, int, str]:
    extension = document_extension(file.filename)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{uuid.uuid4().hex}{extension}"
    size = 0
    try:
        with open(destination, "wb") as out:
            first = True
            while True:
                chunk = await file.read(SAMPLE_BYTES if first else CHUNK)
                if not chunk:
                    break
                if first:
                    validate_document_head(chunk, extension)
                    first = False
                size += len(chunk)
                if size > max_bytes:
                    raise FileTooLargeError(f"File exceeds the {max_bytes // (1024 * 1024)} MB limit")
                out.write(chunk)
            if size == 0:
                raise InvalidDocumentError("The document is empty")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination, size, sanitize_filename(file.filename)
