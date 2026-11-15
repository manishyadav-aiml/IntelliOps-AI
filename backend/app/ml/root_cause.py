"""Deterministic root-cause EVIDENCE for an incident (no LLM, no training).

It compares the incident window with the period just before it and reports facts an engineer would look for first:
  * which services' errors started earliest (temporal precedence),
  * error templates that appear in the incident but never in the baseline (new failure modes),
  * templates whose rate jumped sharply,
  * templates that were frequent before and vanished (often a service that stopped logging because it stopped working).

IMPORTANT: these are correlations in time, NOT proof of causation. Every output carries that disclaimer, and the
results are *suspected* leads for a human, never a confirmed root cause.
"""

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

DISCLAIMER = "Temporal evidence only: earlier or newer is not proof of cause. Treat as leads to verify, not a confirmed root cause."
ERROR_LEVELS = ("ERROR", "CRITICAL")

# (timestamp, level, service, template text)
Entry = tuple[datetime | None, str, str, str]


@dataclass
class ServiceOnset:
    service: str
    first_error_at: datetime
    error_count: int
    seconds_after_first: float


@dataclass
class TemplateFinding:
    template: str
    incident_count: int
    baseline_count: int
    first_seen: datetime | None = None
    rate_ratio: float | None = None


@dataclass
class RcaEvidence:
    earliest_error_services: list[ServiceOnset] = field(default_factory=list)
    new_error_templates: list[TemplateFinding] = field(default_factory=list)
    rate_increases: list[TemplateFinding] = field(default_factory=list)
    disappeared_templates: list[TemplateFinding] = field(default_factory=list)
    baseline_minutes: float = 0.0
    incident_minutes: float = 0.0
    baseline_events: int = 0
    summary: list[str] = field(default_factory=list)
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe dict (datetimes become ISO strings) so it can be stored in a JSON column."""
        return _jsonable(asdict(self))


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _minutes(delta: timedelta) -> float:
    return max(delta.total_seconds() / 60.0, 0.0)


def analyze_incident(entries: list[Entry], start: datetime, end: datetime, lookback: timedelta = timedelta(minutes=30),
                     top_n: int = 5) -> RcaEvidence:
    """`entries` should cover [start - lookback, end]; rows without timestamps are ignored."""
    baseline: list[Entry] = []
    incident: list[Entry] = []
    for entry in entries:
        ts = entry[0]
        if ts is None:
            continue
        if start - lookback <= ts < start:
            baseline.append(entry)
        elif start <= ts < end:
            incident.append(entry)
    result = RcaEvidence(baseline_minutes=round(_minutes(min(lookback, start - min((e[0] for e in baseline), default=start))), 2),
                         incident_minutes=round(_minutes(end - start), 2), baseline_events=len(baseline))
    if not incident:
        result.summary.append("No log entries fall inside the incident window, so no evidence could be derived.")
        return result

    # 1. which services started failing first (within the incident window)
    errors_by_service: dict[str, list[datetime]] = defaultdict(list)
    for ts, level, service, _ in incident:
        if level in ERROR_LEVELS and service != "unknown" and ts is not None:
            errors_by_service[service].append(ts)
    if errors_by_service:
        ordered = sorted(errors_by_service.items(), key=lambda kv: min(kv[1]))
        t0 = min(ordered[0][1])
        result.earliest_error_services = [
            ServiceOnset(s, min(ts_list), len(ts_list), round((min(ts_list) - t0).total_seconds(), 1))
            for s, ts_list in ordered[:top_n]
        ]

    # 2. templates new in the incident, and rate changes (error-level templates only for "new")
    base_counts = Counter(t for _, _, _, t in baseline)
    inc_counts = Counter(t for _, _, _, t in incident)
    inc_first: dict[str, datetime] = {}
    inc_error_templates: set[str] = set()
    for ts, level, _, template in incident:
        if ts is not None and (template not in inc_first or ts < inc_first[template]):
            inc_first[template] = ts
        if level in ERROR_LEVELS:
            inc_error_templates.add(template)
    for template in sorted(inc_error_templates, key=lambda t: -inc_counts[t]):
        if base_counts[template] == 0 and len(result.new_error_templates) < top_n:
            result.new_error_templates.append(TemplateFinding(template, inc_counts[template], 0, inc_first.get(template)))

    base_minutes = max(result.baseline_minutes, 1.0)
    inc_minutes = max(result.incident_minutes, 1.0)
    shifts = []
    for template, count in inc_counts.items():
        if count >= 5 and base_counts[template] > 0:
            ratio = (count / inc_minutes) / (base_counts[template] / base_minutes)
            if ratio >= 3.0:
                shifts.append(TemplateFinding(template, count, base_counts[template], inc_first.get(template), round(ratio, 1)))
    result.rate_increases = sorted(shifts, key=lambda f: -(f.rate_ratio or 0))[:top_n]

    gone = [TemplateFinding(t, 0, c) for t, c in base_counts.items() if c >= 5 and inc_counts[t] == 0]
    result.disappeared_templates = sorted(gone, key=lambda f: -f.baseline_count)[:top_n]

    # human-readable summary (careful wording)
    if len(result.earliest_error_services) >= 1:
        first = result.earliest_error_services[0]
        line = f"Errors began earliest in service '{first.service}' at {first.first_error_at.isoformat()}"
        if len(result.earliest_error_services) > 1:
            nxt = result.earliest_error_services[1]
            gap = f"{nxt.seconds_after_first:.0f}s later" if nxt.seconds_after_first >= 1 else "at about the same time"
            line += f"; '{nxt.service}' followed {gap}"
        result.summary.append(line + ".")
    for f in result.new_error_templates[:3]:
        result.summary.append(f"New error pattern not seen in the previous {result.baseline_minutes:g} min ({f.incident_count} times): {f.template}")
    for f in result.rate_increases[:2]:
        result.summary.append(f"Rate of '{f.template}' rose about {f.rate_ratio:g}x versus the baseline.")
    for f in result.disappeared_templates[:2]:
        result.summary.append(f"'{f.template}' appeared {f.baseline_count} times before the incident and not at all during it (a component may have stopped logging).")
    if result.baseline_events == 0:
        result.summary.append("There is no baseline period before this incident in the file, so 'new' and 'rate' findings are unavailable.")
    if not result.summary:
        result.summary.append("No distinctive onset, new error pattern or rate change was found.")
    return result
