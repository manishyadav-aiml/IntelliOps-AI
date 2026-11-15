"""Incident report rendering (PDF / CSV / JSON) from plain data. No database access here.

AI-generated suggestions and human-confirmed findings are always kept apart and labelled.
"""

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

AI_BANNER = "AI-GENERATED SUGGESTIONS - NOT HUMAN-CONFIRMED. Verify every item against the evidence before acting."
HUMAN_HEADING = "Human-confirmed findings and investigation notes"
MAX_LOG_ROWS = 40


@dataclass
class ReportData:
    incident: dict[str, Any]
    timeline: list[dict[str, Any]] = field(default_factory=list)
    logs: list[dict[str, Any]] = field(default_factory=list)
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    similar_incidents: list[dict[str, Any]] = field(default_factory=list)
    ai_investigation: dict[str, Any] | None = None
    human_notes: list[dict[str, Any]] = field(default_factory=list)
    generated_at: datetime | None = None
    generated_by: str = ""


def _s(value: Any) -> str:
    return "" if value is None else str(value)


def build_json(data: ReportData) -> bytes:
    ai = data.ai_investigation
    payload = {
        "report": {"generated_at": _s(data.generated_at), "generated_by": data.generated_by, "format_version": 1},
        "incident": data.incident,
        "timeline": data.timeline,
        "supporting_logs": data.logs[:MAX_LOG_ROWS * 5],
        "anomaly_results": data.anomalies,
        "similar_incidents": data.similar_incidents,
        "ai_generated_suggestions": {"label": AI_BANNER, "investigation": ai} if ai else {"label": AI_BANNER, "investigation": None},
        "human_confirmed_findings": {
            "notes": data.human_notes,
            "resolution_notes": data.incident.get("resolution_notes"),
            "status": data.incident.get("status"),
        },
    }
    return json.dumps(payload, indent=2, default=str, ensure_ascii=False).encode("utf-8")


def _csv_safe(value: Any) -> str:
    """Neutralise spreadsheet formula injection (cells starting with = + - @ or tab/CR)."""
    text = _s(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def build_csv(data: ReportData) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["section", "source", "timestamp", "field", "value"])

    def row(section: str, source: str, ts: Any, name: str, value: Any) -> None:
        writer.writerow([section, source, _csv_safe(ts), _csv_safe(name), _csv_safe(value)])

    for key in ("public_id", "title", "service", "severity", "status", "detection_time", "first_occurrence",
                "last_occurrence", "assigned_to", "description"):
        row("incident", "system", "", key, data.incident.get(key))
    for reason in data.incident.get("severity_reasons") or []:
        row("severity_reason", "system", "", "reason", reason)
    for event in data.timeline:
        row("timeline", "system", event.get("timestamp"), event.get("event_type"), event.get("description"))
    for log in data.logs:
        row("supporting_log", "system", log.get("timestamp"), f"{log.get('level')} {log.get('service')}", log.get("message"))
    summary = data.incident.get("anomaly_summary")
    for line in ((summary or {}).get("rca") or {}).get("summary", []) if isinstance(summary, dict) else []:
        row("rca_evidence", "system (deterministic, unconfirmed)", "", "finding", line)
    for a in data.anomalies:
        row("anomaly", "model", a.get("window_start"), "score/threshold", f"{a.get('anomaly_score')}/{a.get('threshold')} ({a.get('method')})")
    for s in data.similar_incidents:
        row("similar_incident", "system", "", s.get("similar_incident_id"), f"similarity {s.get('similarity_score')}")
    ai = data.ai_investigation
    if ai:
        row("ai_suggestion", "AI (unconfirmed)", "", "summary", ai.get("incident_summary"))
        for key in ("potential_contributing_factors", "suspected_root_causes", "recommended_investigation"):
            for item in ai.get(key) or []:
                row("ai_suggestion", "AI (unconfirmed)", "", key, item.get("text") if isinstance(item, dict) else item)
        row("ai_suggestion", "AI (unconfirmed)", "", "confidence", ai.get("confidence"))
    for note in data.human_notes:
        row("human_note", f"human: {note.get('author', '')}", note.get("timestamp"), "note", note.get("content"))
    if data.incident.get("resolution_notes"):
        row("human_note", "human", "", "resolution_notes", data.incident["resolution_notes"])
    return out.getvalue().encode("utf-8-sig")


def build_pdf(data: ReportData) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
                            title=f"Incident report {data.incident.get('public_id', '')}")
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10)
    banner = ParagraphStyle("banner", parent=body, backColor=colors.HexColor("#fff4ce"), borderPadding=6, textColor=colors.HexColor("#7a5b00"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=colors.HexColor("#1e3a8a"), spaceBefore=12)

    def p(text: Any, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(escape(_s(text)).replace("\n", "<br/>"), style)

    def table(rows: list[list[Any]], widths: list[float], header: bool = True) -> Table:
        cells = [[p(c, small) for c in r] for r in rows]
        t = Table(cells, colWidths=widths, repeatRows=1 if header else 0)
        style = [("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "TOP")]
        if header:
            style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")))
        t.setStyle(TableStyle(style))
        return t

    inc = data.incident
    flow: list[Any] = [Paragraph(f"Incident Report {escape(_s(inc.get('public_id')))}", styles["Title"]), p(inc.get("title"), styles["Heading3"])]
    flow.append(p(f"Generated {_s(data.generated_at)} by {data.generated_by or 'unknown'}", small))
    flow.append(Paragraph("Incident summary", h2))
    summary = [["Severity", inc.get("severity")], ["Status", inc.get("status")], ["Affected service", inc.get("service")],
               ["Detection time", inc.get("detection_time")], ["First occurrence", inc.get("first_occurrence")],
               ["Last occurrence", inc.get("last_occurrence")], ["Assigned to", inc.get("assigned_to") or "unassigned"]]
    flow.append(table(summary, [4 * cm, 13 * cm], header=False))
    if inc.get("description"):
        flow += [Spacer(1, 6), p(inc["description"])]
    if inc.get("severity_reasons"):
        flow += [Paragraph("Severity explanation (rule-based)", h2)] + [p(f"- {r}") for r in inc["severity_reasons"]]

    flow.append(Paragraph("Timeline", h2))
    flow.append(table([["Time", "Event", "Description"]] + [[e.get("timestamp"), e.get("event_type"), e.get("description")] for e in data.timeline], [4 * cm, 3.5 * cm, 9.5 * cm])
                if data.timeline else p("No timeline events recorded."))

    rca = (inc.get("anomaly_summary") or {}).get("rca") if isinstance(inc.get("anomaly_summary"), dict) else None
    flow.append(Paragraph("Root-cause evidence (deterministic, unconfirmed)", h2))
    if rca and rca.get("summary"):
        flow += [p(f"- {line}") for line in rca["summary"]]
        flow.append(p(rca.get("disclaimer", ""), small))
    else:
        flow.append(p("No deterministic root-cause evidence is available for this incident."))

    flow.append(Paragraph("Anomaly results", h2))
    flow.append(table([["Window start", "Score", "Threshold", "Method", "Service"]] + [[a.get("window_start"), a.get("anomaly_score"), a.get("threshold"), a.get("method"), a.get("affected_service")] for a in data.anomalies], [4 * cm, 2 * cm, 2.5 * cm, 4.5 * cm, 4 * cm])
                if data.anomalies else p("No anomaly records linked to this incident."))
    flow.append(p("Anomaly scores are model-specific and are not probabilities.", small))

    flow.append(Paragraph("Supporting logs", h2))
    shown = data.logs[:MAX_LOG_ROWS]
    flow.append(table([["Time", "Level", "Service", "Message"]] + [[l.get("timestamp"), l.get("level"), l.get("service"), _s(l.get("message"))[:300]] for l in shown], [3.6 * cm, 1.8 * cm, 3 * cm, 8.6 * cm])
                if shown else p("No supporting log entries linked."))
    if len(data.logs) > len(shown):
        flow.append(p(f"Showing {len(shown)} of {len(data.logs)} linked entries.", small))

    flow.append(Paragraph("Similar incidents", h2))
    flow.append(table([["Incident", "Similarity", "Shared services", "Shared templates"]] + [[s.get("similar_incident_id"), s.get("similarity_score"), ", ".join(s.get("shared_services") or []), ", ".join(s.get("shared_templates") or [])] for s in data.similar_incidents], [3 * cm, 2.4 * cm, 4.6 * cm, 7 * cm])
                if data.similar_incidents else p("No similar incidents found."))
    flow.append(p("Similarity indicates comparable symptoms, not a confirmed common root cause.", small))

    ai = data.ai_investigation
    flow += [Paragraph("AI investigation", h2), Paragraph(escape(AI_BANNER), banner), Spacer(1, 6)]
    if not ai:
        flow.append(p("No AI investigation was run for this incident."))
    else:
        flow.append(p(ai.get("incident_summary")))
        for title, key in (("Potential contributing factors", "potential_contributing_factors"), ("Suspected root causes (unconfirmed)", "suspected_root_causes"), ("Recommended actions for a human to evaluate", "recommended_investigation")):
            items = ai.get(key) or []
            flow.append(p(f"<b>{escape(title)}</b>".replace("&lt;", "<"), body))
            flow += [p(f"- {i.get('text') if isinstance(i, dict) else i}  [{', '.join(i.get('evidence', [])) if isinstance(i, dict) else ''}]") for i in items] or [p("None reported.")]
        flow.append(p(f"Model confidence: {ai.get('confidence')}. Limitations: {'; '.join(ai.get('limitations') or []) or 'none stated'}", small))

    flow.append(Paragraph(HUMAN_HEADING, h2))
    if data.human_notes:
        flow.append(table([["Time", "Author", "Note"]] + [[n.get("timestamp"), n.get("author"), n.get("content")] for n in data.human_notes], [4 * cm, 3 * cm, 10 * cm]))
    else:
        flow.append(p("No human investigation notes recorded."))
    flow.append(p(f"Resolution notes: {inc.get('resolution_notes') or 'none'}"))
    flow.append(p(f"Resolution status: {inc.get('status')}"))
    doc.build(flow)
    return buffer.getvalue()
