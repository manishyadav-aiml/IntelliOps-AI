"""Regex-based log line parsing, message masking and parameter extraction.

Dependency-free on purpose: this module is also the fallback when Drain3 is unavailable.
Unavailable fields are reported as "unknown" (level: "UNKNOWN", timestamp: None); the original
line is never discarded by callers.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

UNKNOWN = "unknown"
LEVEL_UNKNOWN = "UNKNOWN"

LEVEL_ALIASES = {
    "DEBUG": "DEBUG", "TRACE": "DEBUG", "FINE": "DEBUG",
    "INFO": "INFO", "NOTICE": "INFO",
    "WARN": "WARNING", "WARNING": "WARNING",
    "ERROR": "ERROR", "ERR": "ERROR", "SEVERE": "ERROR",
    "CRITICAL": "CRITICAL", "CRIT": "CRITICAL", "FATAL": "CRITICAL",
    "EMERG": "CRITICAL", "EMERGENCY": "CRITICAL", "ALERT": "CRITICAL",
}  # fmt: skip

ALLOWED_GROUPS = {"timestamp", "level", "service", "hostname", "message", "date", "time"}

_TS = r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"

# Ordered most specific -> most generic. First pattern whose level word (if any) is valid wins.
BUILTIN_PATTERNS: list[tuple[str, str]] = [
    ("iso_level_bracket_service",
     rf"^(?P<timestamp>{_TS})\s+(?P<level>[A-Za-z]+)\s+\[(?P<service>[^\]]+)\]\s*(?:-\s*)?(?P<message>.*)$"),
    ("iso_level_service_colon",
     rf"^(?P<timestamp>{_TS})\s+(?P<level>[A-Za-z]+)\s+(?P<service>[\w.$\-]+):\s+(?P<message>.*)$"),
    ("iso_level",
     rf"^(?P<timestamp>{_TS})\s+(?P<level>[A-Za-z]+)\s+(?P<message>.*)$"),
    ("bracketed_timestamp",
     r"^\[(?P<timestamp>[^\]]+)\]\s+\[(?P<level>[A-Za-z]+)\]\s*(?:(?P<service>[\w.\-]+):\s+)?(?P<message>.*)$"),
    ("hdfs",
     r"^(?P<date>\d{6})\s+(?P<time>\d{6})\s+\d+\s+(?P<level>[A-Z]+)\s+(?P<service>[\w.$\-]+):\s+(?P<message>.*)$"),
    ("syslog",
     r"^(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s\d{2}:\d{2}:\d{2})\s+(?P<hostname>\S+)\s+(?P<service>[\w.\-/]+)(?:\[\d+\])?:\s+(?P<message>.*)$"),
]  # fmt: skip

_HOST_IN_MESSAGE = re.compile(r"\b(?:host|hostname)=([A-Za-z0-9_.\-]+)")
_SERVICE_IN_MESSAGE = re.compile(r"\b(?:service|svc)=([A-Za-z0-9_.\-]+)")
_LEVEL_KEYWORDS = re.compile(
    r"\b(fatal|critical|panic|error|exception|failed|failure|warn(?:ing)?)\b", re.IGNORECASE
)

# Masks applied (in order) to build templates; shared with the Drain3 integration.
MASK_PATTERNS: list[str] = [
    r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b",  # UUID
    r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b",  # IPv4[:port]
    r"\b0x[0-9a-fA-F]+\b",  # hex literal
    r"(?<![A-Za-z])\d+(?:\.\d+)?",  # numbers (not glued to a preceding letter)
]
_COMPILED_MASKS = [re.compile(p) for p in MASK_PATTERNS]
PLACEHOLDER = "<*>"


@dataclass
class ParserConfig:
    """Parsing configuration. `extra_patterns` are tried before the built-in ones."""

    extra_patterns: list[str] = field(default_factory=list)
    default_year: int | None = None  # used for timestamps without a year (syslog)


@dataclass
class ParsedFields:
    timestamp: datetime | None
    level: str
    service: str
    hostname: str
    message: str
    matched_pattern: str | None
    level_inferred: bool = False


def normalize_level(raw: str | None) -> str:
    if not raw:
        return LEVEL_UNKNOWN
    return LEVEL_ALIASES.get(raw.strip().upper(), LEVEL_UNKNOWN)


def parse_timestamp(text: str | None, default_year: int | None = None) -> datetime | None:
    """Parse common timestamp formats to timezone-aware UTC. Naive values are assumed UTC."""
    if not text:
        return None
    value = text.strip()
    try:
        if value.isdigit() and len(value) in (10, 13):
            seconds = int(value) / (1000 if len(value) == 13 else 1)
            return datetime.fromtimestamp(seconds, tz=UTC)
        dt = datetime.fromisoformat(value.replace(",", "."))
    except (ValueError, OverflowError, OSError):
        dt = None
        for fmt in ("%y%m%d %H%M%S", "%Y/%m/%d %H:%M:%S", "%d/%b/%Y:%H:%M:%S"):
            try:
                dt = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            try:
                dt = datetime.strptime(
                    f"{default_year or datetime.now(UTC).year} {' '.join(value.split())}",
                    "%Y %b %d %H:%M:%S",
                )
            except ValueError:
                return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def compile_custom_patterns(patterns: list[str]) -> list[tuple[str, re.Pattern[str]]]:
    """Validate and compile user-supplied patterns (named groups only from ALLOWED_GROUPS)."""
    compiled = []
    for index, pattern in enumerate(patterns):
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"Invalid custom log pattern #{index + 1}: {exc}") from exc
        names = set(regex.groupindex)
        if "message" not in names:
            raise ValueError(f"Custom log pattern #{index + 1} must define a (?P<message>...) group")
        unknown = names - ALLOWED_GROUPS
        if unknown:
            raise ValueError(f"Custom log pattern #{index + 1} has unsupported groups: {sorted(unknown)}")
        compiled.append((f"custom_{index + 1}", regex))
    return compiled


class LineParser:
    """Parses single log lines. Remembers the last matching pattern to try it first."""

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()
        custom = compile_custom_patterns(self.config.extra_patterns)
        builtin = [(name, re.compile(p)) for name, p in BUILTIN_PATTERNS]
        self._patterns = custom + builtin
        self._last = 0

    def parse(self, line: str) -> ParsedFields:
        text = line.strip()
        order = [self._last, *[i for i in range(len(self._patterns)) if i != self._last]]
        for index in order:
            name, regex = self._patterns[index]
            match = regex.match(text)
            if not match:
                continue
            groups = {k: v for k, v in match.groupdict().items() if v is not None}
            level_word = groups.get("level")
            if level_word is not None and normalize_level(level_word) == LEVEL_UNKNOWN:
                continue  # looked like a level position but is not a real level -> try next pattern
            self._last = index
            return self._build(groups, name)
        return ParsedFields(None, LEVEL_UNKNOWN, UNKNOWN, UNKNOWN, text, None)

    def _build(self, groups: dict[str, str], pattern_name: str) -> ParsedFields:
        message = groups.get("message", "").strip()
        ts_text = groups.get("timestamp")
        if ts_text is None and "date" in groups and "time" in groups:
            ts_text = f"{groups['date']} {groups['time']}"
        level = normalize_level(groups.get("level"))
        inferred = False
        if level == LEVEL_UNKNOWN and pattern_name == "syslog":
            keyword = _LEVEL_KEYWORDS.search(message)
            if keyword:
                level, inferred = normalize_level(_keyword_to_level(keyword.group(1))), True
        host = groups.get("hostname") or _first_group(_HOST_IN_MESSAGE, message) or UNKNOWN
        service = groups.get("service") or _first_group(_SERVICE_IN_MESSAGE, message) or UNKNOWN
        return ParsedFields(
            timestamp=parse_timestamp(ts_text, self.config.default_year),
            level=level,
            service=service,
            hostname=host,
            message=message,
            matched_pattern=pattern_name,
            level_inferred=inferred,
        )


def _first_group(regex: re.Pattern[str], text: str) -> str | None:
    match = regex.search(text)
    return match.group(1) if match else None


def _keyword_to_level(word: str) -> str:
    word = word.lower()
    if word in ("fatal", "critical", "panic"):
        return "CRITICAL"
    if word.startswith("warn"):
        return "WARNING"
    return "ERROR"


def mask_message(message: str) -> str:
    """Replace variable tokens (numbers, IPs, UUIDs, hex) with <*>."""
    for regex in _COMPILED_MASKS:
        message = regex.sub(PLACEHOLDER, message)
    return message


def extract_parameters(template: str, message: str) -> list[str]:
    """Return the values in `message` that fill each <*> in `template` (empty list if no match)."""
    if PLACEHOLDER not in template or len(message) > 4000 or template.count(PLACEHOLDER) > 30:
        return []
    pieces = [re.escape(p) for p in template.split(PLACEHOLDER)]
    match = re.match("^" + "(.*?)".join(pieces) + "$", " ".join(message.split()), re.DOTALL)
    return list(match.groups()) if match else []
