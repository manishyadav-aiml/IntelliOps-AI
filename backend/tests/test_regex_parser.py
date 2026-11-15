from datetime import UTC, datetime

import pytest

from app.parsers.regex_parser import (
    LineParser,
    ParserConfig,
    compile_custom_patterns,
    extract_parameters,
    mask_message,
    normalize_level,
    parse_timestamp,
)


def test_iso_bracket_service_line() -> None:
    p = LineParser().parse("2026-03-01 10:15:32,123 ERROR [payment-service] Gateway timeout host=app-01")
    assert p.timestamp == datetime(2026, 3, 1, 10, 15, 32, 123000, tzinfo=UTC)
    assert (p.level, p.service, p.hostname) == ("ERROR", "payment-service", "app-01")
    assert p.message == "Gateway timeout host=app-01"
    assert p.matched_pattern == "iso_level_bracket_service"


def test_iso_service_colon_line() -> None:
    p = LineParser().parse("2026-03-01T10:15:32Z WARN auth-service: Slow login")
    assert (p.level, p.service, p.message) == ("WARNING", "auth-service", "Slow login")
    assert p.timestamp == datetime(2026, 3, 1, 10, 15, 32, tzinfo=UTC)


def test_timezone_offsets_are_converted_to_utc() -> None:
    p = LineParser().parse("2026-03-01T10:00:00+05:30 INFO api started")
    assert p.timestamp == datetime(2026, 3, 1, 4, 30, tzinfo=UTC)


def test_hdfs_line() -> None:
    p = LineParser().parse(
        "081109 203615 148 INFO dfs.DataNode$PacketResponder: PacketResponder 1 for block blk_38865049064139660 terminating"
    )
    assert p.timestamp == datetime(2008, 11, 9, 20, 36, 15, tzinfo=UTC)
    assert (p.level, p.service) == ("INFO", "dfs.DataNode$PacketResponder")


def test_syslog_line_infers_level_only_from_keywords() -> None:
    parser = LineParser(ParserConfig(default_year=2026))
    err = parser.parse("Mar  1 10:15:32 web-01 sshd[123]: Failed password for root")
    assert (err.hostname, err.service, err.level, err.level_inferred) == ("web-01", "sshd", "ERROR", True)
    assert err.timestamp == datetime(2026, 3, 1, 10, 15, 32, tzinfo=UTC)
    plain = parser.parse("Mar  1 10:15:33 web-01 cron[9]: job started")
    assert plain.level == "UNKNOWN" and plain.level_inferred is False


def test_missing_timestamp_and_unknown_format_are_preserved() -> None:
    p = LineParser().parse("something totally unstructured happened")
    assert p.timestamp is None
    assert (p.level, p.service, p.hostname) == ("UNKNOWN", "unknown", "unknown")
    assert p.message == "something totally unstructured happened"
    assert p.matched_pattern is None


def test_invalid_level_word_does_not_match_level_pattern() -> None:
    p = LineParser().parse("2026-03-01 10:00:00 BANANA something")
    assert p.matched_pattern is None and p.level == "UNKNOWN"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("warn", "WARNING"), ("FATAL", "CRITICAL"), ("err", "ERROR"), ("Info", "INFO"), ("zzz", "UNKNOWN"), (None, "UNKNOWN")],
)
def test_level_normalisation(raw: str | None, expected: str) -> None:
    assert normalize_level(raw) == expected


def test_parse_timestamp_variants() -> None:
    assert parse_timestamp("1772359532") == datetime.fromtimestamp(1772359532, tz=UTC)
    assert parse_timestamp("not a time") is None
    assert parse_timestamp(None) is None


def test_custom_pattern_takes_priority_and_is_validated() -> None:
    config = ParserConfig(extra_patterns=[r"^(?P<level>[A-Z]+)\|(?P<service>\w+)\|(?P<message>.*)$"])
    p = LineParser(config).parse("ERROR|billing|card declined")
    assert (p.level, p.service, p.message, p.matched_pattern) == ("ERROR", "billing", "card declined", "custom_1")
    with pytest.raises(ValueError):
        compile_custom_patterns([r"(?P<level>x)"])  # no message group
    with pytest.raises(ValueError):
        compile_custom_patterns(["(unclosed"])
    with pytest.raises(ValueError):
        compile_custom_patterns([r"(?P<message>.*)(?P<bogus>x)"])


def test_masking_and_parameter_extraction() -> None:
    msg = "User 102 connected to server 192.168.1.1"
    template = mask_message(msg)
    assert template == "User <*> connected to server <*>"
    assert extract_parameters(template, msg) == ["102", "192.168.1.1"]
    assert extract_parameters("no placeholders", "no placeholders") == []
    assert extract_parameters(template, "completely different") == []
