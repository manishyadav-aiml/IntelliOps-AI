"""Transparent rule-based incident severity (P1-P4) with human-readable reasons.

A supervised classifier is intentionally NOT implemented: it needs labelled severity data, which
LogHub datasets do not contain.
"""

from dataclasses import dataclass, field

SEVERITY_LABELS = {"P1": "CRITICAL", "P2": "HIGH", "P3": "MEDIUM", "P4": "LOW"}


@dataclass
class SeverityInput:
    error_count: int  # ERROR + CRITICAL events
    critical_count: int
    total_events: int
    affected_services: int
    anomaly_score: float = 0.0
    anomaly_threshold: float = 0.0
    duration_seconds: float = 0.0
    affected_requests: int | None = None
    historical_p1_matches: int = 0  # similar past incidents that were P1 (if available)


@dataclass
class SeverityResult:
    severity: str
    reasons: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return SEVERITY_LABELS[self.severity]


def classify_severity(inp: SeverityInput) -> SeverityResult:
    rate = inp.error_count / inp.total_events if inp.total_events else 0.0
    ratio = inp.anomaly_score / inp.anomaly_threshold if inp.anomaly_threshold > 0 else 0.0
    reasons: list[str] = []

    p1: list[str] = []
    if inp.critical_count >= 3:
        p1.append(f"{inp.critical_count} CRITICAL log events")
    if rate >= 0.5 and inp.affected_services >= 2 and inp.error_count >= 10:
        p1.append(f"High error rate ({rate:.0%}) across {inp.affected_services} services")
    if ratio >= 2.0 and inp.error_count >= 20:
        p1.append(f"Anomaly score {ratio:.1f}x above threshold with {inp.error_count} errors")
    if inp.historical_p1_matches >= 1 and inp.error_count >= 10:
        p1.append("Matches a previous P1 incident pattern")
    if inp.affected_requests is not None and inp.affected_requests >= 1000:
        p1.append(f"{inp.affected_requests} requests affected")
    if p1:
        return SeverityResult("P1", p1)

    p2: list[str] = []
    if inp.critical_count >= 1:
        p2.append(f"{inp.critical_count} CRITICAL log event(s)")
    if inp.error_count >= 20:
        p2.append(f"{inp.error_count} error events")
    if rate >= 0.3 and inp.error_count >= 5:
        p2.append(f"Elevated error rate ({rate:.0%})")
    if inp.affected_services >= 3 and inp.error_count >= 5:
        p2.append(f"Errors in {inp.affected_services} services")
    if ratio >= 1.5 and inp.error_count >= 5:
        p2.append(f"Anomaly score {ratio:.1f}x above threshold")
    if p2:
        return SeverityResult("P2", p2)

    if inp.error_count >= 3:
        reasons.append(f"{inp.error_count} error events")
    if ratio >= 1.0:
        reasons.append("Anomaly score above threshold")
    if reasons:
        return SeverityResult("P3", reasons)
    return SeverityResult("P4", ["Few or no errors; weak anomaly signal"])
