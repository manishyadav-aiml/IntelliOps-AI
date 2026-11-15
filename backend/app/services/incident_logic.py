"""Pure incident rules: grouping anomalous windows, de-duplication, status transitions, statistics."""

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

INCIDENT_STATUSES = ("OPEN", "INVESTIGATING", "MITIGATED", "RESOLVED")
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"INVESTIGATING", "MITIGATED", "RESOLVED"},
    "INVESTIGATING": {"OPEN", "MITIGATED", "RESOLVED"},
    "MITIGATED": {"INVESTIGATING", "RESOLVED"},
    "RESOLVED": {"OPEN", "INVESTIGATING"},  # re-open
}


class InvalidTransitionError(ValueError):
    pass


def validate_transition(old: str, new: str) -> None:
    if old == new:
        return
    if new not in ALLOWED_TRANSITIONS.get(old, set()):
        raise InvalidTransitionError(f"Cannot change status from {old} to {new}")


class WindowLike(Protocol):
    window_start: datetime
    window_end: datetime
    anomaly_detected: bool
    anomaly_score: float
    affected_service: str


@dataclass
class IncidentCandidate:
    start: datetime
    end: datetime
    primary_service: str
    services: list[str]
    window_count: int
    max_score: float
    detections: list[WindowLike] = field(default_factory=list, repr=False)


def group_anomalous_windows(results: Iterable[WindowLike], window_seconds: int, max_gap_windows: int = 2) -> list[IncidentCandidate]:
    """Merge anomalous windows into episodes so one burst yields ONE incident, not one per window."""
    anomalous = sorted((r for r in results if r.anomaly_detected), key=lambda r: r.window_start)
    max_gap = timedelta(seconds=window_seconds * (max_gap_windows + 1))
    episodes: list[list[WindowLike]] = []
    for result in anomalous:
        if episodes and result.window_start - episodes[-1][-1].window_end < max_gap:
            episodes[-1].append(result)
        else:
            episodes.append([result])
    candidates = []
    for episode in episodes:
        weight: dict[str, float] = {}
        for r in episode:
            weight[r.affected_service] = weight.get(r.affected_service, 0.0) + r.anomaly_score
        ordered = sorted(weight, key=lambda s: weight[s], reverse=True)
        candidates.append(
            IncidentCandidate(
                start=episode[0].window_start,
                end=episode[-1].window_end,
                primary_service=ordered[0],
                services=ordered,
                window_count=len(episode),
                max_score=max(r.anomaly_score for r in episode),
                detections=episode,
            )
        )
    return candidates


def fingerprint(owner_id: int, upload_id: int, primary_service: str, start: datetime) -> str:
    raw = f"{owner_id}|{upload_id}|{primary_service}|{start.isoformat()}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]  # noqa: S324 (identifier, not security)


def ranges_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime, grace: timedelta) -> bool:
    return a_start <= b_end + grace and b_start <= a_end + grace


@dataclass
class RangeStats:
    total_events: int
    error_count: int  # ERROR + CRITICAL
    critical_count: int
    warning_count: int
    services: list[str]
    error_services: list[str]


def stats_for_entries(entries: Iterable[tuple[str, str]]) -> RangeStats:
    """entries = (level, service). Unknown services are ignored for service counts."""
    total = errors = critical = warnings = 0
    services: dict[str, int] = {}
    error_services: dict[str, int] = {}
    for level, service in entries:
        total += 1
        if service != "unknown":
            services[service] = services.get(service, 0) + 1
        if level in ("ERROR", "CRITICAL"):
            errors += 1
            if service != "unknown":
                error_services[service] = error_services.get(service, 0) + 1
        critical += level == "CRITICAL"
        warnings += level == "WARNING"
    rank = lambda d: sorted(d, key=lambda s: d[s], reverse=True)  # noqa: E731
    return RangeStats(total, errors, critical, warnings, rank(services), rank(error_services))


def incident_public_id(numeric_id: int) -> str:
    return f"INC-{1000 + numeric_id}"


def parse_public_id(public_id: str) -> int | None:
    """'INC-1001' -> 1 (numeric id). Returns None for anything else."""
    if public_id.startswith("INC-") and public_id[4:].isdigit():
        value = int(public_id[4:]) - 1000
        return value if value > 0 else None
    return None
