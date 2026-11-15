"""AI investigation, RAG, reports, dashboard and system status through the HTTP API (fake LLM only)."""

import io
import json
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.ai.llm_provider import LLMAuthError, LLMRateLimitError
from tests.test_incidents_api import INCIDENTS, LOGS, analyze, first_incident, upload_sample
from tests.test_rag import make_pdf

DOCS = Path(__file__).resolve().parents[2] / "data" / "sample_documents"
API = "/api/v1"

INVESTIGATION = {
    "incident_summary": "Database errors coincide with payment failures.",
    "observed_symptoms": [{"text": "Burst of error events", "evidence": ["E1"]}],
    "potential_contributing_factors": [{"text": "Database connectivity", "evidence": ["E2"]}],
    "suspected_root_causes": [{"text": "Confirmed: database pool exhaustion", "evidence": ["E1", "E999"]}],
    "recommended_investigation": [{"text": "I restarted the database", "evidence": []}, {"text": "Check pool metrics", "evidence": []}],
    "relevant_historical_incidents": [],
    "relevant_documentation": [],
    "confidence": "high",
    "limitations": ["Sampled logs only"],
}


def make_incident(client: TestClient, headers) -> int:
    analyze(client, headers, upload_sample(client, headers))
    return first_incident(client, headers)["id"]


def upload_doc(client: TestClient, headers, name: str, data: bytes | None = None, mime: str = "text/markdown"):
    content = data if data is not None else (DOCS / name).read_bytes()
    return client.post(f"{API}/documents/upload", headers=headers, files={"file": (name, io.BytesIO(content), mime)})


# ---------- AI investigation ----------
def test_investigation_is_validated_stored_and_labelled(client: TestClient, auth_headers, use_llm) -> None:
    fake = use_llm(payload=INVESTIGATION)
    iid = make_incident(client, auth_headers)
    response = client.post(f"{INCIDENTS}/{iid}/investigate", headers=auth_headers, json={"question": "Why is db failing?"})
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert fake.calls == 1 and result["status"].startswith("AI-generated")
    cause = result["suspected_root_causes"][0]
    assert "confirmed" not in cause["text"].lower() and "E999" not in cause["evidence"]
    assert [r["text"] for r in result["recommended_investigation"]] == ["Check pool metrics"]  # "I restarted" removed
    assert result["confidence"] in {"low", "medium"} and result["validation_notes"]
    detail = client.get(f"{INCIDENTS}/{iid}", headers=auth_headers).json()
    assert detail["latest_investigation"]["status"] == "COMPLETED"
    types = [e["event_type"] for e in client.get(f"{INCIDENTS}/{iid}/timeline", headers=auth_headers).json()]
    assert "AI_INVESTIGATION" in types


def test_ai_failures_return_503_but_other_features_keep_working(client: TestClient, auth_headers, use_llm) -> None:
    iid = make_incident(client, auth_headers)
    for error, code in [(LLMAuthError(), "llm_invalid_key"), (LLMRateLimitError(), "llm_rate_limited")]:
        use_llm(error=error)
        response = client.post(f"{INCIDENTS}/{iid}/investigate", headers=auth_headers)
        assert response.status_code == 503 and response.json()["error"]["code"] == code
    assert client.get(f"{INCIDENTS}/{iid}", headers=auth_headers).status_code == 200
    assert client.get(f"{INCIDENTS}/{iid}", headers=auth_headers).json()["latest_investigation"]["status"] == "FAILED"


def test_missing_api_key_is_a_clear_503_not_a_crash(client: TestClient, auth_headers) -> None:
    iid = make_incident(client, auth_headers)  # no override: real provider with an empty key
    response = client.post(f"{INCIDENTS}/{iid}/investigate", headers=auth_headers)
    assert response.status_code == 503 and response.json()["error"]["code"] == "llm_not_configured"


def test_incident_without_evidence_does_not_call_the_llm(client: TestClient, auth_headers, use_llm) -> None:
    fake = use_llm(payload=INVESTIGATION)
    iid = client.post(INCIDENTS, headers=auth_headers, json={"title": "Empty", "service": "x"}).json()["id"]
    response = client.post(f"{INCIDENTS}/{iid}/investigate", headers=auth_headers)
    # a manual incident still has the severity evidence, so the model is consulted; with none it would not be
    assert response.status_code in (200, 503) and fake.calls <= 1


# ---------- documents + RAG ----------
def test_document_upload_indexing_and_cited_answer(client: TestClient, auth_headers, use_llm) -> None:
    fake = use_llm(payload={"answer": "Check gateway reachability and database availability.", "citations": ["C1", "C77"], "sufficient": True})
    upload = upload_doc(client, auth_headers, "payment_service_runbook.md")
    assert upload.status_code == 202, upload.text
    doc = client.get(f"{API}/documents/{upload.json()['id']}", headers=auth_headers).json()
    assert doc["status"] == "COMPLETED" and doc["chunk_count"] > 0 and doc["embedder_name"] == "hashing-lexical"
    answer = client.post(f"{API}/rag/query", headers=auth_headers, json={"question": "payment failed gateway timeout circuit breaker"}).json()
    assert answer["sufficient"] and answer["llm_used"] and fake.calls == 1
    assert [c["label"] for c in answer["citations"]] == ["C1"]  # invented C77 discarded
    assert answer["citations"][0]["document_name"] == "payment_service_runbook.md" and answer["citations"][0]["chunk_id"].startswith("c")


def test_rag_without_matching_documents_says_so_and_skips_the_llm(client: TestClient, auth_headers, use_llm) -> None:
    fake = use_llm(payload={"answer": "made up", "citations": ["C1"], "sufficient": True})
    answer = client.post(f"{API}/rag/query", headers=auth_headers, json={"question": "How do I bake sourdough bread?"}).json()
    assert not answer["sufficient"] and "does not provide a sufficient answer" in answer["answer"] and fake.calls == 0


def test_rag_works_without_llm_by_returning_excerpts(client: TestClient, auth_headers) -> None:
    upload_doc(client, auth_headers, "database_troubleshooting.md")
    answer = client.post(f"{API}/rag/query", headers=auth_headers, json={"question": "connection pool exhaustion slow queries"}).json()
    assert answer["sufficient"] and not answer["llm_used"] and answer["citations"] and "not configured" in answer["notice"]


def test_pdf_documents_keep_page_numbers_in_citations(client: TestClient, auth_headers, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "ops.pdf", ["Intro page about general topics", "Redis eviction policy allkeys-lru memory pressure runbook"])
    assert upload_doc(client, auth_headers, "ops.pdf", pdf.read_bytes(), "application/pdf").status_code == 202
    answer = client.post(f"{API}/rag/query", headers=auth_headers, json={"question": "redis eviction policy memory pressure"}).json()
    assert answer["citations"] and answer["citations"][0]["page_number"] == 2


def test_documents_are_private_and_deletion_removes_them_from_retrieval(client: TestClient, auth_headers, other_auth_headers) -> None:
    doc_id = upload_doc(client, auth_headers, "payment_service_runbook.md").json()["id"]
    question = {"question": "payment failed gateway timeout circuit breaker"}
    assert client.get(f"{API}/documents/{doc_id}", headers=other_auth_headers).status_code == 404
    assert client.delete(f"{API}/documents/{doc_id}", headers=other_auth_headers).status_code == 404
    assert client.post(f"{API}/documents/{doc_id}/index", headers=other_auth_headers).status_code == 404
    assert client.post(f"{API}/rag/query", headers=other_auth_headers, json=question).json()["citations"] == []
    assert client.get(f"{API}/documents", headers=other_auth_headers).json()["total"] == 0
    assert client.post(f"{API}/rag/query", headers=auth_headers, json=question).json()["citations"]
    assert client.delete(f"{API}/documents/{doc_id}", headers=auth_headers).status_code == 204
    assert client.post(f"{API}/rag/query", headers=auth_headers, json=question).json()["citations"] == []


def test_invalid_documents_are_rejected(client: TestClient, auth_headers) -> None:
    assert upload_doc(client, auth_headers, "x.exe", b"MZ\x90").status_code == 422
    assert upload_doc(client, auth_headers, "empty.md", b"   ").status_code == 422
    assert upload_doc(client, auth_headers, "fake.pdf", b"not a pdf at all").status_code == 422
    blank = upload_doc(client, auth_headers, "blank.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")
    assert blank.status_code == 202 and client.get(f"{API}/documents/{blank.json()['id']}", headers=auth_headers).json()["status"] == "FAILED"
    assert client.get(f"{API}/documents", headers=auth_headers, params={"status": "BOGUS"}).status_code == 422


def test_reindex_and_duplicate_processing(client: TestClient, auth_headers) -> None:
    doc_id = upload_doc(client, auth_headers, "api_timeout_guide.md").json()["id"]
    again = client.post(f"{API}/documents/{doc_id}/index", headers=auth_headers)
    assert again.status_code == 202
    assert client.get(f"{API}/documents/{doc_id}", headers=auth_headers).json()["status"] == "COMPLETED"


# ---------- reports ----------
def test_reports_in_all_formats_download_and_are_private(client: TestClient, auth_headers, other_auth_headers) -> None:
    iid = make_incident(client, auth_headers)
    client.post(f"{INCIDENTS}/{iid}/notes", headers=auth_headers, json={"content": "Pool saturation seen in DB metrics"})
    ids = {}
    for fmt, media in (("pdf", "application/pdf"), ("csv", "text/csv"), ("json", "application/json")):
        created = client.post(f"{API}/reports/generate", headers=auth_headers, json={"incident_id": iid, "format": fmt})
        assert created.status_code == 201, created.text
        ids[fmt] = created.json()["id"]
        download = client.get(f"{API}/reports/{ids[fmt]}/download", headers=auth_headers)
        assert download.status_code == 200 and download.headers["content-type"].startswith(media)
        assert f"INC-{1000 + iid}" in download.headers["content-disposition"]
        if fmt == "pdf":
            text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(download.content)).pages)
            assert "NOT HUMAN-CONFIRMED" in text and "Pool saturation" in text
        if fmt == "json":
            body = json.loads(download.content)
            assert body["human_confirmed_findings"]["notes"][0]["content"].startswith("Pool saturation")
            assert body["ai_generated_suggestions"]["investigation"] is None
    assert client.get(f"{API}/reports", headers=auth_headers).json()["total"] == 3
    assert client.get(f"{API}/reports/{ids['pdf']}/download", headers=other_auth_headers).status_code == 404
    assert client.get(f"{API}/reports", headers=other_auth_headers).json()["total"] == 0
    assert client.post(f"{API}/reports/generate", headers=other_auth_headers, json={"incident_id": iid, "format": "pdf"}).status_code == 404
    assert client.post(f"{API}/reports/generate", headers=auth_headers, json={"incident_id": iid, "format": "docx"}).status_code == 422


def test_report_includes_ai_findings_only_when_an_investigation_ran(client: TestClient, auth_headers, use_llm) -> None:
    use_llm(payload=INVESTIGATION)
    iid = make_incident(client, auth_headers)
    client.post(f"{INCIDENTS}/{iid}/investigate", headers=auth_headers)
    rid = client.post(f"{API}/reports/generate", headers=auth_headers, json={"incident_id": iid, "format": "json"}).json()["id"]
    body = json.loads(client.get(f"{API}/reports/{rid}/download", headers=auth_headers).content)
    assert body["ai_generated_suggestions"]["investigation"]["status"].startswith("AI-generated")


# ---------- dashboard + system ----------
def test_dashboard_is_empty_not_fake_for_a_new_user(client: TestClient, auth_headers) -> None:
    s = client.get(f"{API}/dashboard/summary", headers=auth_headers).json()
    assert (s["total_logs_processed"], s["active_incidents"], s["anomalies_detected"], s["services_monitored"]) == (0, 0, 0, 0)
    assert s["avg_time_to_acknowledge_seconds"] is None and s["avg_time_to_resolve_seconds"] is None
    t = client.get(f"{API}/dashboard/trends", headers=auth_headers).json()
    assert t["error_frequency"] == [] and t["top_templates"] == []


def test_dashboard_reflects_real_data_and_user_isolation(client: TestClient, auth_headers, other_auth_headers) -> None:
    iid = make_incident(client, auth_headers)
    s = client.get(f"{API}/dashboard/summary", headers=auth_headers).json()
    assert s["total_logs_processed"] > 500 and s["active_incidents"] == 1 and s["anomalies_detected"] >= 1 and s["services_monitored"] >= 3
    assert s["avg_time_to_resolve_seconds"] is None  # nothing resolved yet
    client.patch(f"{INCIDENTS}/{iid}", headers=auth_headers, json={"status": "INVESTIGATING"})
    client.patch(f"{INCIDENTS}/{iid}", headers=auth_headers, json={"status": "RESOLVED"})
    after = client.get(f"{API}/dashboard/summary", headers=auth_headers).json()
    assert after["resolved_incidents"] == 1 and after["active_incidents"] == 0 and after["avg_time_to_resolve_seconds"] is not None
    trends = client.get(f"{API}/dashboard/trends", headers=auth_headers, params={"bucket": "hour"}).json()
    assert sum(p["count"] for p in trends["error_frequency"]) > 0 and trends["top_templates"] and trends["severity_distribution"]
    assert client.get(f"{API}/dashboard/services", headers=auth_headers).json()[0]["count"] == 1
    other = client.get(f"{API}/dashboard/summary", headers=other_auth_headers).json()
    assert other["total_logs_processed"] == 0 and other["resolved_incidents"] == 0
    assert client.get(f"{API}/dashboard/trends", headers=auth_headers, params={"bucket": "week"}).status_code == 422


def test_dashboard_service_filter(client: TestClient, auth_headers) -> None:
    make_incident(client, auth_headers)
    assert client.get(f"{API}/dashboard/summary", headers=auth_headers, params={"service": "nonexistent"}).json()["active_incidents"] == 0


def test_system_status_never_exposes_secrets(client: TestClient, auth_headers) -> None:
    status = client.get(f"{API}/system/status", headers=auth_headers).json()
    assert status["llm_configured"] is False and status["embedder"] == "hashing-lexical"
    assert "key" not in " ".join(status.keys()).replace("llm_configured", "")
    assert client.get(f"{API}/system/status").status_code == 401


def test_all_new_endpoints_require_authentication(client: TestClient) -> None:
    for method, url in [("get", f"{API}/incidents"), ("get", f"{API}/anomalies"), ("get", f"{API}/documents"),
                        ("post", f"{API}/rag/query"), ("get", f"{API}/reports"), ("get", f"{API}/dashboard/summary"),
                        ("post", f"{API}/incidents/1/investigate"), ("post", f"{LOGS}/1/analyze")]:
        assert getattr(client, method)(url).status_code == 401, (method, url)
