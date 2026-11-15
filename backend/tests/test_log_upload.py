import asyncio
from pathlib import Path

import pytest

from app.services.log_upload import (
    FileTooLargeError,
    InvalidFileError,
    sanitize_filename,
    save_upload,
    validate_extension,
    validate_sample,
)


class FakeUpload:
    def __init__(self, filename: str | None, data: bytes) -> None:
        self.filename = filename
        self._data = data
        self._pos = 0

    async def read(self, size: int = -1) -> bytes:
        end = len(self._data) if size < 0 else self._pos + size
        chunk, self._pos = self._data[self._pos : end], end
        return chunk


def run(coro):
    return asyncio.run(coro)


def test_sanitize_filename_strips_paths_and_odd_characters() -> None:
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\Users\\me\\app<1>.log") == "app_1_.log"
    assert sanitize_filename(None) == "upload"


@pytest.mark.parametrize("name", ["a.exe", "a.log.exe", "noext", "a.pdf", None])
def test_bad_extensions_rejected(name: str | None) -> None:
    with pytest.raises(InvalidFileError):
        validate_extension(name)


@pytest.mark.parametrize("name", ["a.log", "A.TXT", "x.csv"])
def test_good_extensions_accepted(name: str) -> None:
    assert validate_extension(name) in {".log", ".txt", ".csv"}


@pytest.mark.parametrize(
    "sample",
    [b"", b"   \n  ", b"MZ\x90\x00 fake exe", b"\x7fELF\x02", b"#!/bin/sh\nrm -rf /", b"text\x00more", b"PK\x03\x04zip", b"\xff\xfe\xfd" * 50],
)
def test_bad_content_rejected_even_with_log_extension(sample: bytes) -> None:
    with pytest.raises(InvalidFileError):
        validate_sample(sample, ".log")


def test_csv_requires_message_column() -> None:
    with pytest.raises(InvalidFileError):
        validate_sample(b"a,b\n1,2\n", ".csv")
    validate_sample(b"time,message\n1,hello\n", ".csv")


def test_save_upload_writes_server_named_file(tmp_path: Path) -> None:
    path, size, display = run(
        save_upload(FakeUpload("../../evil name.log", b"2026-03-01 10:00:00 INFO ok\n"), tmp_path, 1024)
    )
    assert path.parent == tmp_path and path.suffix == ".log" and "evil" not in path.name
    assert size == 28 and display == "evil name.log" and path.read_bytes().startswith(b"2026")


def test_save_upload_enforces_size_and_cleans_up(tmp_path: Path) -> None:
    with pytest.raises(FileTooLargeError):
        run(save_upload(FakeUpload("a.log", b"line of text\n" * 100), tmp_path, 100))
    assert list(tmp_path.iterdir()) == []


def test_save_upload_rejects_empty_and_cleans_up(tmp_path: Path) -> None:
    with pytest.raises(InvalidFileError):
        run(save_upload(FakeUpload("a.log", b""), tmp_path, 100))
    assert list(tmp_path.iterdir()) == []
