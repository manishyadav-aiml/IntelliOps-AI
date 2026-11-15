"""Anomaly detection -> incidents -> lifecycle, through the HTTP API (uses the synthetic sample incident log)."""

import io
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "sample_logs"
LOGS, INCIDENTS = "/api/v1/logs", "/api/v1/incidents"


def upload_sample(client: TestClient, headers: dict[str, str], name: str = "incident_payment_failure.log") -> int:
    data = (SAMPLES / name).read_bytes()
    response = client.post(f"{LOGS}/upload", headers=headers, files={"file": (name, io.BytesIO(data), "text/plain")})
    assert response.status_code == 202, response.text
    assert client.get(f"{LOGS}/{response.json()['id']}", headers=headers).json()["status"] == "COMPLETED"
    return response.json()["id"]


def analyze(client: TestClient, headers: dict[str, str], log_id: int, **params):
    return client.post(f"{LOGS}/{log_id}/analyze", headers=headers, params=params)


def first_incident(client: TestClient, headers: dict[str, str]) -> dict:
    items = client.get(INCIDENTS, headers=headers).json()["items"]
    assert items, "expected at least one incident"
    return items[0]


def test_analysis_creates_one_grouped_incident_not_one_per_window(client: TestClient, auth_headers) -> None:
    log_id = upload_sample(client, auth_headers)
    result = analyze(client, auth_headers, log_id)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["windows_analyzed"] > 5 and body["anomalous_windows"] >= 1
    assert body["incidents_created"] == 1 and "baseline" in body["method"]
    assert "not a probability" in body["note"]
    assert client.get(INCIDENTS, headers=auth_headers).json()["total"] == 1


def test_analysis_is_idempotent_and_never_duplicates_incidents(client: TestClient, auth_headers) -> None:
    log_id = upload_sample(client, auth_headers)
    analyze(client, auth_headers, log_id)
    again = analyze(client, auth_headers, log_id).json()
    assert again["incidents_created"] == 0
    assert client.get(INCIDENTS, headers=auth_headers).json()["total"] == 1
    anomalies = client.get("/api/v1/anomalies", headers=auth_headers, params={"upload_id": log_id}).json()
    assert anomalies["total"] == again["windows_analyzed"]  # replaced, not appended


def test_normal_traffic_creates_no_incident(client: TestClient, auth_headers) -> None:
    log_id = upload_sample(client, auth_headers, "normal_activity.log")
    body = analyze(client, auth_headers, log_id).json()
    assert body["anomalous_windows"] == 0 and body["incidents_created"] == 0


def test_analysis_requires_a_parsed_file_and_valid_window(client: TestClient, auth_headers) -> None:
    log_id = upload_sample(client, auth_headers)
    assert analyze(client, auth_headers, log_id, window_seconds=5).status_code == 422
    assert analyze(client, auth_headers, 99999).status_code == 404


def test_incident_detail_has_severity_explanation_and_real_timeline(client: TestClient, auth_headers) -> None:
    analyze(client, auth_headers, upload_sample(client, auth_headers))
    summary = first_incident(client, auth_headers)
    assert summary["public_id"] == f"INC-{1000 + summary['id']}" and summary["severity"] in {"P1", "P2"}
    detail = client.get(f"{INCIDENTS}/{summary['id']}", headers=auth_headers).json()
    assert detail["severity_reasons"] and detail["linked_log_count"] > 0 and detail["templates"]
    assert "not a probability" in detail["anomaly_summary"]["note"]
    events = client.get(f"{INCIDENTS}/{summary['id']}/timeline", headers=auth_headers).json()
    types = [e["event_type"] for e in events]
    assert {"ABNORMAL_ACTIVITY", "ANOMALY_DETECTED", "INCIDENT_CREATED"} <= set(types)
    assert [e["timestamp"] for e in events] == sorted(e["timestamp"] for e in events)
    only = client.get(f"{INCIDENTS}/{summary['id']}/timeline", headers=auth_headers, params={"event_type": "INCIDENT_CREATED"}).json()
    assert [e["event_type"] for e in only] == ["INCIDENT_CREATED"]


def test_status_lifecycle_timestamps_and_invalid_transitions(client: TestClient, auth_headers) -> None:
    analyze(client, auth_headers, upload_sample(client, auth_headers))
    iid = first_incident(client, auth_headers)["id"]
    url = f"{INCIDENTS}/{iid}"
    assert client.patch(url, headers=auth_headers, json={"status": "INVESTIGATING"}).json()["acknowledged_at"] is not None
    assert client.patch(url, headers=auth_headers, json={"status": "OPEN"}).status_code == 200  # allowed step back
    bad = client.patch(url, headers=auth_headers, json={"status": "MITIGATED"})
    assert bad.status_code == 200
    assert client.patch(url, headers=auth_headers, json={"status": "OPEN"}).status_code == 409  # MITIGATED -> OPEN not allowed
    resolved = client.patch(url, headers=auth_headers, json={"status": "RESOLVED", "resolution_notes": "pool resized"}).json()
    assert resolved["resolved_at"] is not None and resolved["resolution_notes"] == "pool resized"
    assert client.patch(url, headers=auth_headers, json={"status": "INVESTIGATING"}).json()["resolved_at"] is None  # reopened
    assert client.patch(url, headers=auth_headers, json={"status": "BOGUS"}).status_code == 422


def test_severity_change_is_recorded_with_who_and_what(client: TestClient, auth_headers, db_session: Session) -> None:
    analyze(client, auth_headers, upload_sample(client, auth_headers))
    incident = first_incident(client, auth_headers)
    new = "P3" if incident["severity"] != "P3" else "P2"
    assert client.patch(f"{INCIDENTS}/{incident['id']}", headers=auth_headers, json={"severity": new}).json()["severity"] == new
    events = client.get(f"{INCIDENTS}/{incident['id']}/timeline", headers=auth_headers, params={"event_type": "SEVERITY_CHANGED"}).json()
    assert events[0]["details"] == {"from": incident["severity"], "to": new} and "Ada Lovelace" in events[0]["description"]
    audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "incident.severity_changed"))
    assert audit is not None and audit.details == {"from": incident["severity"], "to": new} and audit.user_id is not None


def test_notes_and_assignment(client: TestClient, auth_headers) -> None:
    analyze(client, auth_headers, upload_sample(client, auth_headers))
    iid = first_incident(client, auth_headers)["id"]
    note = client.post(f"{INCIDENTS}/{iid}/notes", headers=auth_headers, json={"content": "DB pool looked saturated"})
    assert note.status_code == 201 and note.json()["author_name"] == "Ada Lovelace"
    assert client.post(f"{INCIDENTS}/{iid}/notes", headers=auth_headers, json={"content": ""}).status_code == 422
    me = client.get("/api/v1/auth/me", headers=auth_headers).json()["id"]
    assigned = client.patch(f"{INCIDENTS}/{iid}", headers=auth_headers, json={"assigned_user_id": me}).json()
    assert assigned["assigned_to"] == "Ada Lovelace" and assigned["notes"][0]["content"] == "DB pool looked saturated"
    assert client.patch(f"{INCIDENTS}/{iid}", headers=auth_headers, json={"assigned_user_id": me + 99}).status_code == 422
    assert client.patch(f"{INCIDENTS}/{iid}", headers=auth_headers, json={"assigned_user_id": None}).json()["assigned_user_id"] is None


def test_manual_incident_filters_search_and_sorting(client: TestClient, auth_headers) -> None:
    for title, sev, svc in [("Disk almost full", "P3", "storage"), ("Checkout outage", "P1", "payment"), ("Slow search", "P4", "search")]:
        response = client.post(INCIDENTS, headers=auth_headers, json={"title": title, "severity": sev, "service": svc})
        assert response.status_code == 201
    assert client.post(INCIDENTS, headers=auth_headers, json={"title": "  "}).status_code == 422
    assert client.get(INCIDENTS, headers=auth_headers, params={"severity": "P1"}).json()["total"] == 1
    assert client.get(INCIDENTS, headers=auth_headers, params={"q": "disk"}).json()["items"][0]["service"] == "storage"
    assert client.get(INCIDENTS, headers=auth_headers, params={"service": "search"}).json()["total"] == 1
    ordered = client.get(INCIDENTS, headers=auth_headers, params={"sort_by": "severity", "order": "asc"}).json()["items"]
    assert [i["severity"] for i in ordered] == ["P1", "P3", "P4"]
    assert client.get(INCIDENTS, headers=auth_headers, params={"page_size": 2}).json()["items"].__len__() == 2


def test_similar_incidents_are_found_but_never_across_users(client: TestClient, auth_headers, other_auth_headers) -> None:
    ids = [client.post(INCIDENTS, headers=auth_headers, json={"title": t, "service": "payment-service", "severity": "P2"}).json()["id"]
           for t in ("Payment gateway timeout errors", "Payment gateway timeout again")]
    client.post(INCIDENTS, headers=other_auth_headers, json={"title": "Payment gateway timeout errors", "service": "payment-service"})
    similar = client.get(f"{INCIDENTS}/{ids[1]}/similar", headers=auth_headers).json()
    assert [s["similar_incident_pk"] for s in similar] == [ids[0]]  # the other user's identical incident is invisible
    assert "not a confirmed common root cause" in similar[0]["note"]


def test_incidents_are_isolated_between_users(client: TestClient, auth_headers, other_auth_headers) -> None:
    analyze(client, auth_headers, upload_sample(client, auth_headers))
    iid = first_incident(client, auth_headers)["id"]
    url = f"{INCIDENTS}/{iid}"
    for call in (client.get(url, headers=other_auth_headers), client.get(f"{url}/timeline", headers=other_auth_headers),
                 client.get(f"{url}/similar", headers=other_auth_headers),
                 client.patch(url, headers=other_auth_headers, json={"status": "RESOLVED"}),
                 client.post(f"{url}/notes", headers=other_auth_headers, json={"content": "x"}),
                 client.post(f"{url}/investigate", headers=other_auth_headers)):
        assert call.status_code == 404
    assert client.get(INCIDENTS, headers=other_auth_headers).json()["total"] == 0
    assert client.get("/api/v1/anomalies", headers=other_auth_headers).json()["total"] == 0


def test_manual_incident_cannot_reference_another_users_log(client: TestClient, auth_headers, other_auth_headers) -> None:
    log_id = upload_sample(client, auth_headers, "normal_activity.log")
    assert client.post(INCIDENTS, headers=other_auth_headers, json={"title": "x", "upload_id": log_id}).status_code == 404
