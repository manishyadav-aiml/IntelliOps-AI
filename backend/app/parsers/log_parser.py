"""Streaming reader for .log/.txt/.csv files. Never loads a whole file into memory."""

import csv
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.parsers.regex_parser import (
    LEVEL_UNKNOWN,
    UNKNOWN,
    LineParser,
    ParserConfig,
    normalize_level,
    parse_timestamp,
)

CSV_ALIASES = {
    "timestamp": {"timestamp", "time", "@timestamp", "datetime", "date", "ts"},
    "level": {"level", "severity", "loglevel", "log_level", "lvl"},
    "service": {"service", "component", "app", "application", "logger", "source"},
    "hostname": {"host", "hostname", "node", "server"},
    "message": {"message", "msg", "log", "text", "content", "description"},
}


class LogParseError(Exception):
    """The file cannot be parsed at all (for example a CSV without a message column)."""


@dataclass
class ParsedRecord:
    line_number: int
    raw: str
    timestamp: datetime | None
    level: str
    service: str
    hostname: str
    message: str
    truncated: bool = False
    matched_pattern: str | None = None
    level_inferred: bool = False


@dataclass
class ParseStats:
    total_lines: int = 0  # physical lines/rows read (excluding CSV header)
    empty_lines: int = 0
    entries: int = 0  # non-empty records
    structured_entries: int = 0  # matched a known pattern / CSV row
    unstructured_entries: int = 0  # stored as-is with unknown fields
    truncated_lines: int = 0
    level_inferred: int = 0
    encoding_replacements: int = 0
    pattern_counts: dict[str, int] = field(default_factory=dict)
    template_count: int = 0
    parser_used: str = ""
    extractor_errors: int = 0

    def to_dict(self) -> dict[str, object]:
        return dict(self.__dict__)


def iter_lines(path: Path, max_len: int) -> Iterator[tuple[int, str, bool]]:
    """Yield (line_number, text, truncated). Over-long lines are cut, the remainder skipped."""
    with open(path, encoding="utf-8-sig", errors="replace", newline=None) as handle:
        number = 0
        while True:
            chunk = handle.readline(max_len + 1)
            if chunk == "":
                return
            number += 1
            truncated = False
            if len(chunk) > max_len and not chunk.endswith("\n"):
                truncated = True
                while True:  # discard the rest of this physical line in small reads
                    rest = handle.readline(65536)
                    if rest == "" or rest.endswith("\n"):
                        break
                chunk = chunk[:max_len]
            yield number, chunk.rstrip("\r\n"), truncated


def _map_csv_columns(header: list[str]) -> dict[str, int]:
    normalized = [h.strip().lower() for h in header]
    mapping: dict[str, int] = {}
    for target, aliases in CSV_ALIASES.items():
        for index, name in enumerate(normalized):
            if name in aliases and target not in mapping:
                mapping[target] = index
                break
    return mapping


def _iter_csv(path: Path, config: ParserConfig, max_len: int) -> Iterator[ParsedRecord]:
    csv.field_size_limit(max_len * 10)
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel  # type: ignore[assignment]
        reader = csv.reader(handle, dialect)
        header = next(reader, None)
        if header is None:
            return
        columns = _map_csv_columns(header)
        if "message" not in columns:
            raise LogParseError("CSV file must contain a message column (message, msg, log, text)")
        for row_number, row in enumerate(reader, start=2):
            if not any(cell.strip() for cell in row):
                yield ParsedRecord(row_number, "", None, LEVEL_UNKNOWN, UNKNOWN, UNKNOWN, "")
                continue

            def cell(name: str, row: list[str] = row) -> str:
                index = columns.get(name)
                return row[index].strip() if index is not None and index < len(row) else ""

            message = cell("message")
            truncated = len(message) > max_len
            yield ParsedRecord(
                line_number=row_number,
                raw=",".join(row)[:max_len],
                timestamp=parse_timestamp(cell("timestamp"), config.default_year),
                level=normalize_level(cell("level")),
                service=cell("service") or UNKNOWN,
                hostname=cell("hostname") or UNKNOWN,
                message=message[:max_len],
                truncated=truncated,
                matched_pattern="csv",
            )


def iter_records(path: Path, config: ParserConfig, max_len: int = 10_000) -> Iterator[ParsedRecord]:
    """Yield one record per physical line/row. Empty lines yield records with message == ''."""
    if path.suffix.lower() == ".csv":
        yield from _iter_csv(path, config, max_len)
        return
    parser = LineParser(config)
    for number, text, truncated in iter_lines(path, max_len):
        if not text.strip():
            yield ParsedRecord(number, text, None, LEVEL_UNKNOWN, UNKNOWN, UNKNOWN, "")
            continue
        fields = parser.parse(text)
        yield ParsedRecord(
            line_number=number,
            raw=text,
            timestamp=fields.timestamp,
            level=fields.level,
            service=fields.service,
            hostname=fields.hostname,
            message=fields.message,
            truncated=truncated,
            matched_pattern=fields.matched_pattern,
            level_inferred=fields.level_inferred,
        )


def update_stats(stats: ParseStats, record: ParsedRecord) -> None:
    stats.total_lines += 1
    if not record.message.strip() and not record.raw.strip():
        stats.empty_lines += 1
        return
    stats.entries += 1
    if record.matched_pattern:
        stats.structured_entries += 1
        counts = Counter(stats.pattern_counts)
        counts[record.matched_pattern] += 1
        stats.pattern_counts = dict(counts)
    else:
        stats.unstructured_entries += 1
    stats.truncated_lines += int(record.truncated)
    stats.level_inferred += int(record.level_inferred)
    stats.encoding_replacements += record.raw.count("\ufffd")
