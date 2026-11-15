import io
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.models.log import LogEntry, LogUpload

UPLOAD = "/api/v1/logs/upload"
LOGS = "/api/v1/logs"

SAMPLE = (
    "2026-03-01 10:00:00,100 INFO [api-gateway] Request 101 from 10.0.0.1 completed in 35 ms\n"
    "2026-03-01 10:00:01,200 INFO [api-gateway] Request 102 from 10.0.0.2 completed in 41 ms\n"
    "2026-03-01 10:00:02,300 ERROR [payment-service] Payment 9001 failed: gateway timeout host=pay-01\n"
    "2026-03-01 10:00:03,400 ERROR [payment-service] Payment 9002 failed: gateway timeout host=pay-01\n"
    "\n"
    "2026-03-01 10:00:04,500 WARN [db] Connection pool at 91 percent\n"
    "totally unstructured line without any format\n"
)


def upload(client: TestClient, headers: dict[str, str], content: str | bytes = SAMPLE, name: str = "app.log"):
    data = content.encode() if isinstance(content, str) else content
    return client.post(UPLOAD, headers=headers, files={"file": (name, io.BytesIO(data), "text/plain")})


def test_upload_requires_authentication(client: TestClient) -> None:
    assert upload(client, {}).status_code == 401


def test_upload_parses_in_background_and_stores_entries(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = upload(client, auth_headers)
    assert response.status_code == 202
    body = response.json()
    assert body["filename"] == "app.log" and body["status"] in {"PENDING", "PROCESSING", "COMPLETED"}
    detail = client.get(f"{LOGS}/{body['id']}", headers=auth_headers).json()
    assert detail["status"] == "COMPLETED"
    assert detail["total_lines"] == 7 and detail["entry_count"] == 6
    assert detail["parse_stats"]["empty_lines"] == 1
    assert detail["parse_stats"]["unstructured_entries"] == 1
    assert detail["parse_stats"]["template_count"] >= 3
    assert detail["parser_used"] == "regex"


def test_entries_keep_original_message_and_unknown_fields(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    log_id = upload(client, auth_headers).json()["id"]
    items = client.get(f"{LOGS}/{log_id}/entries", headers=auth_headers).json()["items"]
    assert [i["line_number"] for i in items] == [1, 2, 3, 4, 6, 7]
    first, unstructured = items[0], items[-1]
    assert first["level"] == "INFO" and first["service"] == "api-gateway"
    assert first["original_message"].startswith("2026-03-01 10:00:00,100 INFO")
    assert first["source_file"] == "app.log"
    assert first["template_text"] == "Request <*> from <*> completed in <*> ms"
    assert first["parameters"] == ["101", "10.0.0.1", "35"]
    assert (unstructured["level"], unstructured["service"], unstructured["timestamp"]) == ("UNKNOWN", "unknown", None)
    assert unstructured["original_message"] == "totally unstructured line without any format"
    assert items[2]["hostname"] == "pay-01"


def test_repeated_messages_share_one_template(client: TestClient, auth_headers: dict[str, str]) -> None:
    log_id = upload(client, auth_headers).json()["id"]
    templates = client.get(f"{LOGS}/{log_id}/templates", headers=auth_headers).json()
    assert templates[0]["occurrences"] == 2
    assert {t["template_text"] for t in templates[:2]} >= {"Request <*> from <*> completed in <*> ms"}


def test_entry_filters_search_sort_and_pagination(client: TestClient, auth_headers: dict[str, str]) -> None:
    log_id = upload(client, auth_headers).json()["id"]
    url = f"{LOGS}/{log_id}/entries"
    errors = client.get(url, headers=auth_headers, params={"level": "error"}).json()
    assert errors["total"] == 2
    by_service = client.get(url, headers=auth_headers, params={"service": "db"}).json()
    assert by_service["total"] == 1
    search = client.get(url, headers=auth_headers, params={"q": "gateway timeout"}).json()
    assert search["total"] == 2
    wildcard = client.get(url, headers=auth_headers, params={"q": "%"}).json()
    assert wildcard["total"] == 0  # LIKE wildcards are escaped
    page = client.get(url, headers=auth_headers, params={"page": 2, "page_size": 4}).json()
    assert page["total"] == 6 and len(page["items"]) == 2
    desc = client.get(url, headers=auth_headers, params={"order": "desc"}).json()["items"]
    assert desc[0]["line_number"] == 7
    window = client.get(
        url, headers=auth_headers,
        params={"start": "2026-03-01T10:00:02Z", "end": "2026-03-01T10:00:03.500Z"},
    ).json()
    assert window["total"] == 2
    assert client.get(url, headers=auth_headers, params={"page_size": 5000}).status_code == 422


def test_facets_list_levels_and_services(client: TestClient, auth_headers: dict[str, str]) -> None:
    log_id = upload(client, auth_headers).json()["id"]
    facets = client.get(f"{LOGS}/{log_id}/facets", headers=auth_headers).json()
    assert {"ERROR", "INFO", "WARNING", "UNKNOWN"} <= set(facets["levels"])
    assert "payment-service" in facets["services"]


def test_csv_upload(client: TestClient, auth_headers: dict[str, str]) -> None:
    csv_text = "timestamp,level,service,message\n2026-03-01 10:00:00,ERROR,auth,Login failed for user 7\n"
    log_id = upload(client, auth_headers, csv_text, "auth.csv").json()["id"]
    entry = client.get(f"{LOGS}/{log_id}/entries", headers=auth_headers).json()["items"][0]
    assert (entry["level"], entry["service"], entry["message"]) == ("ERROR", "auth", "Login failed for user 7")


def test_invalid_uploads_are_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert upload(client, auth_headers, SAMPLE, "malware.exe").status_code == 422
    assert upload(client, auth_headers, b"", "empty.log").status_code == 422
    assert upload(client, auth_headers, b"MZ\x90\x00binary", "fake.log").status_code == 422
    assert upload(client, auth_headers, b"a,b\n1,2\n", "bad.csv").status_code == 422
    body = upload(client, auth_headers, b"", "empty.log").json()
    assert body["error"]["code"] == "invalid_file"
    assert client.get(LOGS, headers=auth_headers).json()["total"] == 0  # nothing persisted


def test_oversized_upload_returns_413_and_leaves_no_file(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    settings = get_settings()
    original = settings.max_upload_size_mb
    settings.max_upload_size_mb = 1
    try:
        big = ("2026-03-01 10:00:00 INFO [api] filler line\n" * 40000).encode()
        assert len(big) > 1024 * 1024
        response = upload(client, auth_headers, big, "big.log")
    finally:
        settings.max_upload_size_mb = original
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_path_traversal_filename_is_neutralised(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = upload(client, auth_headers, SAMPLE, "../../../etc/cron.d/evil.log")
    assert response.status_code == 202
    assert response.json()["filename"] == "evil.log"
    root = Path(get_settings().upload_dir)
    assert not (root.parent / "etc").exists()


def test_users_cannot_see_or_touch_each_others_logs(
    client: TestClient, auth_headers: dict[str, str], other_auth_headers: dict[str, str]
) -> None:
    log_id = upload(client, auth_headers).json()["id"]
    for suffix in ("", "/entries", "/templates", "/facets"):
        assert client.get(f"{LOGS}/{log_id}{suffix}", headers=other_auth_headers).status_code == 404
    assert client.delete(f"{LOGS}/{log_id}", headers=other_auth_headers).status_code == 404
    assert client.post(f"{LOGS}/{log_id}/analyze", headers=other_auth_headers).status_code == 404
    assert client.get(LOGS, headers=other_auth_headers).json()["total"] == 0
    assert client.get(f"{LOGS}/{log_id}", headers=auth_headers).status_code == 200


def test_list_filters_and_search(client: TestClient, auth_headers: dict[str, str]) -> None:
    upload(client, auth_headers, SAMPLE, "alpha.log")
    upload(client, auth_headers, SAMPLE, "beta.txt")
    assert client.get(LOGS, headers=auth_headers).json()["total"] == 2
    assert client.get(LOGS, headers=auth_headers, params={"q": "alp"}).json()["total"] == 1
    assert client.get(LOGS, headers=auth_headers, params={"status": "FAILED"}).json()["total"] == 0
    assert client.get(LOGS, headers=auth_headers, params={"status": "BOGUS"}).status_code == 422


def test_templates_are_shared_across_a_users_uploads(client: TestClient, auth_headers: dict[str, str]) -> None:
    a = upload(client, auth_headers).json()["id"]
    b = upload(client, auth_headers).json()["id"]
    ta = {t["template_id"] for t in client.get(f"{LOGS}/{a}/templates", headers=auth_headers).json()}
    tb = {t["template_id"] for t in client.get(f"{LOGS}/{b}/templates", headers=auth_headers).json()}
    assert ta == tb


def test_delete_removes_entries_file_and_audits(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    log_id = upload(client, auth_headers).json()["id"]
    path = Path(get_settings().upload_dir) / db_session.get(LogUpload, log_id).stored_path
    assert path.exists()
    assert client.delete(f"{LOGS}/{log_id}", headers=auth_headers).status_code == 204
    assert not path.exists()
    assert client.get(f"{LOGS}/{log_id}", headers=auth_headers).status_code == 404
    assert db_session.scalars(select(LogEntry)).first() is None
    assert "log.deleted" in set(db_session.scalars(select(AuditLog.action)))


def test_reprocess_conflicts_when_completed_and_retries_failed(
    client: TestClient, auth_headers: dict[str, str], session_factory
) -> None:
    log_id = upload(client, auth_headers).json()["id"]
    assert client.post(f"{LOGS}/{log_id}/reprocess", headers=auth_headers).status_code == 409
    with session_factory() as db:  # simulate a failure, then retry
        record = db.get(LogUpload, log_id)
        record.status, record.error_message = "FAILED", "boom"
        db.commit()
    retry = client.post(f"{LOGS}/{log_id}/reprocess", headers=auth_headers)
    assert retry.status_code == 202
    detail = client.get(f"{LOGS}/{log_id}", headers=auth_headers).json()
    assert detail["status"] == "COMPLETED" and detail["entry_count"] == 6 and detail["error_message"] is None
    with session_factory() as db:  # retry must not duplicate rows
        assert len(db.scalars(select(LogEntry).where(LogEntry.upload_id == log_id)).all()) == 6


def test_csv_missing_message_column_that_passes_validation_marks_failed(
    client: TestClient, auth_headers: dict[str, str], session_factory
) -> None:
    # header looks fine at upload time ("msg"), file later becomes unparseable only if truly empty of rows
    log_id = upload(client, auth_headers, "msg\n", "headeronly.csv").json()["id"]
    detail = client.get(f"{LOGS}/{log_id}", headers=auth_headers).json()
    assert detail["status"] == "FAILED"
    assert "No log lines" in detail["error_message"]


def test_cannot_delete_while_processing(
    client: TestClient, auth_headers: dict[str, str], session_factory
) -> None:
    log_id = upload(client, auth_headers).json()["id"]
    with session_factory() as db:
        db.get(LogUpload, log_id).status = "PROCESSING"
        db.commit()
    assert client.delete(f"{LOGS}/{log_id}", headers=auth_headers).status_code == 409


def test_duplicate_processing_is_prevented(session_factory, client: TestClient, auth_headers) -> None:
    from app.services.log_processing import LogProcessor

    log_id = upload(client, auth_headers).json()["id"]  # already COMPLETED by the background task
    LogProcessor(session_factory, get_settings()).process(log_id)  # second run must be a no-op
    with session_factory() as db:
        assert len(db.scalars(select(LogEntry).where(LogEntry.upload_id == log_id)).all()) == 6
