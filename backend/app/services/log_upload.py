"""Upload validation and safe storage. Uploaded content is untrusted and is never executed."""

import codecs
import csv
import io
import re
import uuid
from pathlib import Path
from typing import Protocol

from app.core.exceptions import AppError
from app.parsers.log_parser import CSV_ALIASES

ALLOWED_EXTENSIONS = {".log", ".txt", ".csv"}
SAMPLE_BYTES = 64 * 1024
CHUNK_BYTES = 1024 * 1024
_BINARY_MAGIC = (b"MZ", b"\x7fELF", b"PK\x03\x04", b"%PDF", b"#!", b"\x89PNG", b"\x1f\x8b", b"\xca\xfe\xba\xbe")


class InvalidFileError(AppError):
    status_code = 422
    code = "invalid_file"


class FileTooLargeError(AppError):
    status_code = 413
    code = "file_too_large"


class AsyncReadable(Protocol):
    filename: str | None

    async def read(self, size: int = -1) -> bytes: ...


def sanitize_filename(name: str | None) -> str:
    """Display name only: never used to build a filesystem path."""
    base = re.split(r"[\\/]", name or "")[-1]
    base = re.sub(r"[^A-Za-z0-9._ \-]", "_", base).strip(" .")
    return base[:120] or "upload"


def validate_extension(filename: str | None) -> str:
    ext = Path(sanitize_filename(filename)).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidFileError("Only .log, .txt and .csv files are supported")
    return ext


def validate_sample(sample: bytes, extension: str) -> None:
    """Content checks on the first bytes; the extension alone is never trusted."""
    if not sample.strip():
        raise InvalidFileError("The file is empty")
    if sample.startswith(_BINARY_MAGIC):
        raise InvalidFileError("The file looks like a binary or executable file, not a text log")
    if b"\x00" in sample:
        raise InvalidFileError("The file contains binary data (NUL bytes)")
    text = codecs.getincrementaldecoder("utf-8")(errors="replace").decode(sample, final=False)
    if text.count("\ufffd") / max(len(text), 1) > 0.10:
        raise InvalidFileError("The file is not valid UTF-8 text")
    control = sum(1 for c in text if ord(c) < 32 and c not in "\t\n\r\f")
    if control / max(len(text), 1) > 0.02:
        raise InvalidFileError("The file contains too many control characters to be a text log")
    if extension == ".csv":
        first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
        header = next(csv.reader(io.StringIO(first_line)), [])
        names = {h.strip().lower().lstrip("\ufeff") for h in header}
        if not names & CSV_ALIASES["message"]:
            raise InvalidFileError("CSV file must contain a message column (message, msg, log, text)")


async def save_upload(file: AsyncReadable, directory: Path, max_bytes: int) -> tuple[Path, int, str]:
    """Stream the upload to `<directory>/<uuid><ext>`. Returns (path, size_bytes, display_name).

    The stored name is generated server-side, so user-supplied names cannot cause path traversal.
    The file is removed again if any validation fails.
    """
    extension = validate_extension(file.filename)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{uuid.uuid4().hex}{extension}"
    size = 0
    try:
        with open(destination, "wb") as out:
            first = True
            while True:
                chunk = await file.read(SAMPLE_BYTES if first else CHUNK_BYTES)
                if not chunk:
                    break
                if first:
                    validate_sample(chunk, extension)
                    first = False
                size += len(chunk)
                if size > max_bytes:
                    raise FileTooLargeError(f"File exceeds the {max_bytes // (1024 * 1024)} MB limit")
                out.write(chunk)
            if size == 0:
                raise InvalidFileError("The file is empty")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination, size, sanitize_filename(file.filename)
