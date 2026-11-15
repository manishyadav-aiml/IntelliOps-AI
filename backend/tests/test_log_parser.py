from pathlib import Path

import pytest

from app.parsers.log_parser import LogParseError, ParseStats, iter_lines, iter_records, update_stats
from app.parsers.regex_parser import ParserConfig


def write(tmp_path: Path, name: str, content: str | bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content if isinstance(content, bytes) else content.encode())
    return path


def test_iter_lines_numbers_lines_and_handles_crlf(tmp_path: Path) -> None:
    path = write(tmp_path, "a.log", "one\r\ntwo\r\n\r\nthree")
    assert [(n, t) for n, t, _ in iter_lines(path, 100)] == [(1, "one"), (2, "two"), (3, ""), (4, "three")]


def test_long_lines_are_truncated_without_breaking_numbering(tmp_path: Path) -> None:
    path = write(tmp_path, "a.log", "x" * 500 + "\nshort\n")
    lines = list(iter_lines(path, 100))
    assert lines[0][0] == 1 and len(lines[0][1]) == 100 and lines[0][2] is True
    assert lines[1] == (2, "short", False)


def test_invalid_utf8_is_replaced_not_fatal(tmp_path: Path) -> None:
    path = write(tmp_path, "a.log", b"2026-03-01 10:00:00 INFO api bad byte \xff\xfe here\n")
    stats = ParseStats()
    for record in iter_records(path, ParserConfig()):
        update_stats(stats, record)
    assert stats.entries == 1 and stats.encoding_replacements >= 1


def test_text_file_stats_mix_structured_unstructured_and_empty(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        "a.log",
        "2026-03-01 10:00:00 INFO [api] ok\n\nrandom text\n2026-03-01 10:00:05 ERROR [db] boom\n",
    )
    stats = ParseStats()
    records = list(iter_records(path, ParserConfig()))
    for r in records:
        update_stats(stats, r)
    assert (stats.total_lines, stats.empty_lines, stats.entries) == (4, 1, 3)
    assert (stats.structured_entries, stats.unstructured_entries) == (2, 1)
    assert records[2].level == "UNKNOWN" and records[2].message == "random text"
    assert records[3].level == "ERROR"


def test_csv_columns_are_mapped_by_alias(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        "a.csv",
        "Time,Severity,Component,Host,Msg\n2026-03-01 10:00:00,error,payments,h1,Card declined\n,,,,\n",
    )
    records = list(iter_records(path, ParserConfig()))
    assert records[0].level == "ERROR" and records[0].service == "payments"
    assert records[0].hostname == "h1" and records[0].message == "Card declined"
    assert records[0].timestamp is not None and records[0].line_number == 2
    assert records[1].message == ""  # blank row reported as empty


def test_csv_without_message_column_raises(tmp_path: Path) -> None:
    path = write(tmp_path, "a.csv", "a,b\n1,2\n")
    with pytest.raises(LogParseError):
        list(iter_records(path, ParserConfig()))


def test_bom_is_ignored(tmp_path: Path) -> None:
    path = write(tmp_path, "a.log", b"\xef\xbb\xbf2026-03-01 10:00:00 INFO [api] ok\n")
    assert next(iter_records(path, ParserConfig())).level == "INFO"
