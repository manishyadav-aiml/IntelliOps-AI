from datetime import UTC, datetime, timedelta

from app.ml.root_cause import DISCLAIMER, analyze_incident

T0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
START, END = T0 + timedelta(minutes=30), T0 + timedelta(minutes=33)


def baseline(minutes: int = 30, per_minute: int = 6) -> list[tuple]:
    rows = []
    for m in range(minutes):
        for i in range(per_minute):
            ts = T0 + timedelta(minutes=m, seconds=i * 9)
            rows.append((ts, "INFO", "api-gateway", "GET <*> 200"))
            if i % 2 == 0:
                rows.append((ts, "INFO", "metrics-agent", "Heartbeat ok"))  # frequent before, absent during the incident
    return rows


def incident() -> list[tuple]:
    rows = []
    for i in range(12):  # database errors start first
        rows.append((START + timedelta(seconds=5 + i * 3), "ERROR", "db", "Connection timeout after <*> ms"))
    for i in range(10):  # payment errors 20s later
        rows.append((START + timedelta(seconds=25 + i * 3), "ERROR", "payment-service", "Payment <*> failed: database unavailable"))
    for i in range(90):  # gateway traffic jumps to 30/min against a baseline of 6/min (5x)
        rows.append((START + timedelta(seconds=i * 2), "INFO", "api-gateway", "GET <*> 200"))
    return rows


def test_reports_which_service_failed_first_and_how_much_later() -> None:
    result = analyze_incident(baseline() + incident(), START, END)
    first, second = result.earliest_error_services[0], result.earliest_error_services[1]
    assert (first.service, second.service) == ("db", "payment-service")
    assert first.seconds_after_first == 0 and 15 <= second.seconds_after_first <= 25
    assert "Errors began earliest in service 'db'" in result.summary[0] and "'payment-service' followed" in result.summary[0]


def test_finds_new_error_templates_rate_increases_and_vanished_templates() -> None:
    result = analyze_incident(baseline() + incident(), START, END)
    assert {f.template for f in result.new_error_templates} == {"Connection timeout after <*> ms", "Payment <*> failed: database unavailable"}
    assert result.new_error_templates[0].baseline_count == 0
    assert [f.template for f in result.rate_increases] == ["GET <*> 200"] and result.rate_increases[0].rate_ratio >= 3
    assert [f.template for f in result.disappeared_templates] == ["Heartbeat ok"]


def test_every_result_carries_the_not_causation_disclaimer() -> None:
    result = analyze_incident(baseline() + incident(), START, END)
    assert result.disclaimer == DISCLAIMER and "not proof of cause" in result.disclaimer
    assert result.to_dict()["disclaimer"] == DISCLAIMER


def test_without_a_baseline_it_says_so_instead_of_inventing_new_patterns() -> None:
    result = analyze_incident(incident(), START, END)
    assert result.new_error_templates and result.baseline_events == 0
    assert any("no baseline period" in line.lower() for line in result.summary)
    assert result.rate_increases == [] and result.disappeared_templates == []


def test_empty_window_and_untimestamped_rows_are_handled() -> None:
    assert "No log entries fall inside" in analyze_incident(baseline(), START, END).summary[0]
    rows = incident() + [(None, "ERROR", "ghost", "ignored")]
    assert "ghost" not in [s.service for s in analyze_incident(rows, START, END).earliest_error_services]


def test_calm_incident_reports_nothing_distinctive() -> None:
    rows = baseline() + [(START + timedelta(seconds=i * 20), "INFO", "api-gateway", "GET <*> 200") for i in range(9)]
    result = analyze_incident(rows, START, END)
    assert result.earliest_error_services == [] and result.new_error_templates == []


def test_result_is_json_serialisable_for_storage() -> None:
    import json

    payload = json.dumps(analyze_incident(baseline() + incident(), START, END).to_dict())
    assert "Connection timeout" in payload and START.isoformat()[:10] in payload


def test_evidence_builder_includes_the_deterministic_findings() -> None:
    from app.ai.investigation_agent import build_evidence

    rca = analyze_incident(baseline() + incident(), START, END).to_dict()
    items = build_evidence([], [], None, None, [], [], [], rca)
    assert items and all(i.kind == "analysis" for i in items) and "Deterministic log analysis" in items[0].text
    assert build_evidence([], [], None, None, [], [], [], None) == []
