from app.ml.severity_classifier import SeverityInput, classify_severity


def sev(**kw):
    base = dict(error_count=0, critical_count=0, total_events=100, affected_services=1)
    return classify_severity(SeverityInput(**{**base, **kw}))


def test_p1_critical_events_with_reasons() -> None:
    result = sev(error_count=40, critical_count=8, total_events=100, affected_services=2)
    assert result.severity == "P1" and result.label == "CRITICAL"
    assert any("CRITICAL" in r for r in result.reasons)


def test_p1_widespread_high_error_rate() -> None:
    assert sev(error_count=60, total_events=100, affected_services=3).severity == "P1"


def test_p1_from_anomaly_score_and_history() -> None:
    assert sev(error_count=25, anomaly_score=9.0, anomaly_threshold=3.5).severity == "P1"
    assert sev(error_count=12, historical_p1_matches=1).severity == "P1"


def test_p2_high() -> None:
    assert sev(error_count=25).severity == "P2"
    assert sev(critical_count=1, error_count=1).severity == "P2"
    assert sev(error_count=6, total_events=15).severity == "P2"  # 40% error rate


def test_p3_medium() -> None:
    result = sev(error_count=4)
    assert result.severity == "P3" and result.label == "MEDIUM" and result.reasons


def test_p4_low() -> None:
    result = sev(error_count=0)
    assert result.severity == "P4" and result.label == "LOW"


def test_zero_events_does_not_divide_by_zero() -> None:
    assert sev(total_events=0).severity == "P4"
