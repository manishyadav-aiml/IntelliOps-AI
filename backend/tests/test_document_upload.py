import asyncio
from pathlib import Path

import pytest

from app.rag.document_loader import InvalidDocumentError
from app.services.document_upload import save_document
from app.services.log_upload import FileTooLargeError


class FakeUpload:
    def __init__(self, filename, data):
        self.filename, self._data, self._pos = filename, data, 0

    async def read(self, size=-1):
        end = len(self._data) if size < 0 else self._pos + size
        chunk, self._pos = self._data[self._pos:end], end
        return chunk


def run(coro):
    return asyncio.run(coro)


def test_valid_markdown_is_stored_under_a_server_generated_name(tmp_path: Path) -> None:
    path, size, name = run(save_document(FakeUpload("../../runbook one.md", b"# Title\n\ntext"), tmp_path, 1024))
    assert path.parent == tmp_path and path.suffix == ".md" and "runbook" not in path.name
    assert size == 13 and name == "runbook one.md"


@pytest.mark.parametrize(("name", "data"), [("a.exe", b"MZ"), ("a.pdf", b"not a pdf"), ("a.md", b""), ("a.txt", b"a\x00b")])
def test_invalid_documents_are_rejected_and_leave_no_file(tmp_path: Path, name: str, data: bytes) -> None:
    with pytest.raises(InvalidDocumentError):
        run(save_document(FakeUpload(name, data), tmp_path, 1024))
    assert list(tmp_path.iterdir()) == []


def test_size_limit_enforced(tmp_path: Path) -> None:
    with pytest.raises(FileTooLargeError):
        run(save_document(FakeUpload("a.md", b"hello world " * 100), tmp_path, 100))
    assert list(tmp_path.iterdir()) == []
