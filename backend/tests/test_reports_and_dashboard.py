import csv
import io
import json
from datetime import UTC, datetime, timedelta
from io import BytesIO

from pypdf import PdfReader

from app.services.dashboard_logic import average_seconds, bucket_counts, distribution, fill_gaps
from app.services.report_builder import AI_BANNER, HUMAN_HEADING, ReportData, build_csv, build_json, build_pdf

T = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)

AI = {
    "incident_summary": "Payment failures coincide with database connection errors.",
    "potential_contributing_factors": [{"text": "Database refusing connections", "evidence": ["E2"]}],
    "suspected_root_causes": [{"text": "Database connectivity problem", "evidence": ["E2"]}],
    "recommended_investigation": [{"text": "Check connection pool metrics", "evidence": []}],
    "confidence": "medium", "limitations": ["Sample of logs only"],
}


def data(ai=AI, notes=True) -> ReportData:
    return ReportData(
        incident={"public_id": "INC-1001", "title": "Payment failures", "service": "payment-service", "severity": "P1",
                  "status": "RESOLVED", "detection_time": T, "first_occurrence": T, "last_occurrence": T + timedelta(minutes=3),
                  "assigned_to": "Ada", "description": "Burst of payment errors", "severity_reasons": ["8 CRITICAL events"],
                  "resolution_notes": "Pool size increased by the DB team"},
        timeline=[{"timestamp": T, "event_type": "ANOMALY_DETECTED", "description": "Window flagged"}],
        logs=[{"timestamp": T, "level": "ERROR", "service": "payment-service", "message": "gateway timeout <b>&</b>"}],
        anomalies=[{"window_start": T, "anomaly_score": 46.0, "threshold": 3.5, "method": "baseline", "affected_service": "db"}],
        similar_incidents=[{"similar_incident_id": "INC-1000", "similarity_score": 0.71, "shared_services": ["db"], "shared_templates": []}],
        ai_investigation=ai,
        human_notes=[{"author": "Ada", "timestamp": T, "content": "Confirmed pool exhaustion in DB metrics"}] if notes else [],
        generated_at=T, generated_by="ada@example.com",
    )


def pdf_text(pdf: bytes) -> str:
    return "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)


def test_pdf_contains_all_sections_and_the_ai_vs_human_distinction() -> None:
    pdf = build_pdf(data())
    assert pdf.startswith(b"%PDF")
    text = pdf_text(pdf)
    for needle in ("INC-1001", "Payment failures", "P1", "8 CRITICAL events", "ANOMALY_DETECTED", "INC-1000",
                   "Suspected root causes (unconfirmed)", "NOT HUMAN-CONFIRMED", HUMAN_HEADING,
                   "Confirmed pool exhaustion", "Pool size increased", "not probabilities"):
        assert needle in text, needle
    assert text.index("NOT HUMAN-CONFIRMED") < text.index(HUMAN_HEADING)


def test_pdf_escapes_markup_and_handles_missing_sections() -> None:
    text = pdf_text(build_pdf(data()))
    assert "gateway timeout <b>&</b>" in text.replace("\n", " ")
    bare = ReportData(incident={"public_id": "INC-1002", "title": "Minimal"}, generated_at=T)
    out = pdf_text(build_pdf(bare))
    assert "No AI investigation was run" in out and "No timeline events recorded" in out and "No human investigation notes" in out


def test_pdf_caps_long_log_tables() -> None:
    d = data()
    d.logs = [{"timestamp": T, "level": "ERROR", "service": "s", "message": f"line {i}"} for i in range(200)]
    assert "Showing 40 of 200" in pdf_text(build_pdf(d))


def test_json_report_separates_ai_from_human_findings() -> None:
    doc = json.loads(build_json(data()))
    assert doc["incident"]["public_id"] == "INC-1001"
    assert doc["ai_generated_suggestions"]["label"] == AI_BANNER
    assert doc["ai_generated_suggestions"]["investigation"]["confidence"] == "medium"
    assert doc["human_confirmed_findings"]["notes"][0]["author"] == "Ada"
    assert doc["human_confirmed_findings"]["resolution_notes"].startswith("Pool size")
    assert json.loads(build_json(data(ai=None)))["ai_generated_suggestions"]["investigation"] is None


def test_csv_report_labels_sources_and_blocks_formula_injection() -> None:
    d = data()
    d.human_notes = [{"author": "Eve", "timestamp": T, "content": "=HYPERLINK(\"http://evil\",\"x\")"}]
    raw = build_csv(d)
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    assert rows[0] == ["section", "source", "timestamp", "field", "value"]
    sources = {r[0]: r[1] for r in rows if r[0] in ("ai_suggestion", "anomaly")}
    assert sources["ai_suggestion"] == "AI (unconfirmed)" and sources["anomaly"] == "model"
    note = next(r for r in rows if r[0] == "human_note")
    assert note[4].startswith("'=") and note[1].startswith("human")


def test_unicode_survives_all_formats() -> None:
    d = data()
    d.incident["title"] = "Zahlungsfehler für Käufer – 支付失败"
    assert "Zahlungsfehler" in json.loads(build_json(d))["incident"]["title"]
    assert "Zahlungsfehler" in build_csv(d).decode("utf-8-sig")
    build_pdf(d)  # must not raise


# ---------- dashboard aggregation ----------
def test_bucket_counts_and_gap_filling() -> None:
    ts = [T, T + timedelta(minutes=5), T + timedelta(hours=2)]
    series = bucket_counts(ts, "hour")
    assert [p["count"] for p in series] == [2, 1]
    filled = fill_gaps(series, "hour", T, T + timedelta(hours=2))
    assert [p["count"] for p in filled] == [2, 0, 1]


def test_distribution_sorted_by_count() -> None:
    assert distribution(["P2", "P1", "P2", "P3"]) == [{"name": "P2", "count": 2}, {"name": "P1", "count": 1}, {"name": "P3", "count": 1}]


def test_average_seconds_only_uses_complete_pairs_and_none_when_unavailable() -> None:
    assert average_seconds([(T, T + timedelta(seconds=60)), (T, T + timedelta(seconds=120)), (T, None), (None, T)]) == 90.0
    assert average_seconds([(T, None)]) is None
    assert average_seconds([]) is None


def test_reports_include_the_root_cause_evidence_section() -> None:
    d = data()
    d.incident["anomaly_summary"] = {"rca": {"summary": ["Errors began earliest in service 'db'."], "disclaimer": "Temporal evidence only."}}
    text = pdf_text(build_pdf(d))
    assert "Root-cause evidence (deterministic, unconfirmed)" in text and "began earliest in service" in text
    assert any(r[0] == "rca_evidence" for r in csv.reader(io.StringIO(build_csv(d).decode("utf-8-sig"))))
    assert "No deterministic root-cause evidence" in pdf_text(build_pdf(data()))
