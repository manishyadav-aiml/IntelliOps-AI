"""Evidence-grounded incident investigation.

The agent never executes anything. It builds numbered evidence, asks the LLM for structured JSON, then
VALIDATES the answer: unknown evidence ids are removed, claims without valid evidence are dropped,
statements that an action was executed are removed, "confirmed" causes are downgraded to "suspected",
and confidence is capped when the evidence is thin or validation corrections are required.
If there is no evidence the LLM is not called.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from app.ai.llm_provider import (
    LLMError,
    LLMMalformedResponseError,
    LLMNotConfiguredError,
    LLMProvider,
    LLMRequest,
)
from app.ai.prompts import (
    INVESTIGATION_SYSTEM,
    EvidenceItem,
    build_investigation_prompt,
    sanitize_untrusted,
)

MAX_EVIDENCE = 40
AI_STATUS = "AI-generated suggestion - not human-confirmed"

_EXECUTED = re.compile(
    r"\b(i|we)\s+(have\s+)?(restarted|rebooted|deployed|executed|ran|fixed|applied|rolled back|killed)\b"
    r"|\b(has|have|was|were)\s+(been\s+)?(restarted|rebooted|deployed|executed|fixed|applied|rolled back)\b",
    re.IGNORECASE,
)

_CONFIRMED = re.compile(r"\bconfirmed\b", re.IGNORECASE)

LIST_KEYS = [
    "observed_symptoms",
    "potential_contributing_factors",
    "suspected_root_causes",
    "recommended_investigation",
    "relevant_documentation",
]

NEEDS_EVIDENCE = {
    "observed_symptoms",
    "suspected_root_causes",
    "potential_contributing_factors",
    "relevant_documentation",
}


@dataclass
class Investigation:
    incident_summary: str
    observed_symptoms: list[dict] = field(default_factory=list)
    potential_contributing_factors: list[dict] = field(default_factory=list)
    suspected_root_causes: list[dict] = field(default_factory=list)
    recommended_investigation: list[dict] = field(default_factory=list)
    relevant_historical_incidents: list[str] = field(default_factory=list)
    relevant_documentation: list[dict] = field(default_factory=list)
    confidence: str = "low"
    limitations: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    status: str = AI_STATUS
    validation_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class InvestigationOutcome:
    ok: bool
    investigation: Investigation | None = None
    error_code: str | None = None
    error_message: str | None = None


def build_evidence(
    log_samples: list[dict],
    templates: list[dict],
    anomaly: dict | None,
    severity: dict | None,
    similar: list[dict],
    documents: list[dict],
    notes: list[str],
    rca: dict | None = None,
) -> list[EvidenceItem]:
    """Number all available evidence. Inputs are plain dicts so this stays independent of the DB."""

    items: list[EvidenceItem] = []

    def add(kind: str, text: str, source: dict) -> None:
        if len(items) < MAX_EVIDENCE:
            items.append(EvidenceItem(f"E{len(items) + 1}", kind, text, source))

    if anomaly:
        add(
            "anomaly",
            f"Anomaly detected in window {anomaly.get('window_start')} "
            f"(score {anomaly.get('anomaly_score')}, threshold {anomaly.get('threshold')}, "
            f"method {anomaly.get('method')}). Top features: {anomaly.get('features')}",
            anomaly,
        )

    if severity:
        add(
            "severity",
            f"Rule-based severity {severity.get('severity')}: "
            f"{'; '.join(severity.get('reasons', []))}",
            severity,
        )

    if rca:
        # Deterministic, LLM-free findings (temporal evidence, not causation).
        for line in (rca.get("summary") or [])[:6]:
            add(
                "analysis",
                f"Deterministic log analysis: {line}",
                {"kind": "rca"},
            )

    for template in templates:
        seen = (
            f" (seen {template['occurrences']} times)"
            if template.get("occurrences")
            else ""
        )

        add(
            "template",
            f"Log template{seen}: {template['template_text']}",
            template,
        )

    for entry in log_samples:
        add(
            "log",
            f"{entry.get('timestamp')} {entry.get('level')} "
            f"[{entry.get('service')}] {entry['message']}",
            entry,
        )

    for similar_incident in similar:
        add(
            "similar_incident",
            f"Similar incident {similar_incident['incident_id']} "
            f"(similarity {similar_incident['score']}): "
            f"{similar_incident['title']}",
            similar_incident,
        )

    for document in documents:
        add(
            "document",
            f"{document['document']} p.{document.get('page')}: "
            f"{document['text']}",
            document,
        )

    for note in notes:
        add(
            "note",
            note,
            {"kind": "human_note"},
        )

    return items


def _normalise_items(
    raw: Any,
    valid_ids: set[str],
) -> tuple[list[dict], int]:
    """Return (clean items, number of invented evidence references removed)."""

    removed = 0
    clean: list[dict] = []

    for item in raw if isinstance(raw, list) else []:
        text = item.get("text") if isinstance(item, dict) else item

        if not isinstance(text, str) or not text.strip():
            continue

        refs = item.get("evidence", []) if isinstance(item, dict) else []
        refs = refs if isinstance(refs, list) else []

        valid = [
            ref
            for ref in refs
            if isinstance(ref, str) and ref in valid_ids
        ]

        removed += len(refs) - len(valid)

        clean.append({
            "text": text.strip(),
            "evidence": valid,
        })

    return clean, removed


def validate_investigation(
    raw: dict,
    evidence: list[EvidenceItem],
    incident_summary: str,
    valid_incident_ids: set[str] | None = None,
) -> Investigation:

    if not isinstance(raw.get("incident_summary"), str):
        raise LLMMalformedResponseError()

    valid_ids = {item.id for item in evidence}

    notes: list[str] = []

    result = Investigation(
        incident_summary=raw["incident_summary"].strip() or incident_summary
    )

    for key in LIST_KEYS:
        items, invented = _normalise_items(
            raw.get(key),
            valid_ids,
        )

        if invented:
            notes.append(
                f"Removed {invented} reference(s) to evidence "
                f"that does not exist in '{key}'."
            )

        kept = []

        for item in items:

            if _EXECUTED.search(item["text"]):
                notes.append(
                    f"Removed a statement in '{key}' "
                    "claiming an action was executed."
                )
                continue

            if key in NEEDS_EVIDENCE and not item["evidence"]:
                notes.append(
                    f"Dropped an unsupported item from '{key}' "
                    "(no valid evidence reference)."
                )
                continue

            if (
                key == "suspected_root_causes"
                and _CONFIRMED.search(item["text"])
            ):
                item["text"] = _CONFIRMED.sub(
                    "suspected",
                    item["text"],
                )

                notes.append(
                    "Downgraded a 'confirmed' cause to 'suspected'."
                )

            kept.append(item)

        setattr(result, key, kept)

    allowed = valid_incident_ids or set()

    history = raw.get("relevant_historical_incidents")

    result.relevant_historical_incidents = [
        item
        for item in (history if isinstance(history, list) else [])
        if isinstance(item, str) and item in allowed
    ]

    limits = raw.get("limitations")

    result.limitations = [
        sanitize_untrusted(item, 300)
        for item in (limits if isinstance(limits, list) else [])
        if isinstance(item, str)
    ]

    # --------------------------------------------------
    # Confidence validation
    # --------------------------------------------------

    confidence = (
        raw.get("confidence")
        if raw.get("confidence") in ("low", "medium", "high")
        else "low"
    )

    kinds = {item.kind for item in evidence}

    # Rule 1: Thin evidence cannot support high or medium confidence.
    if len(evidence) < 3 or "log" not in kinds:

        if confidence != "low":
            notes.append(
                "Confidence capped at 'low' because the evidence is thin."
            )

        confidence = "low"

    # Rule 2: Validation corrections prevent high confidence.
    elif notes and confidence == "high":

        confidence = "medium"

        notes.append(
            "Confidence capped at 'medium' because the response "
            "required validation corrections."
        )

    result.confidence = confidence

    result.evidence = [
        {
            "id": item.id,
            "kind": item.kind,
            "text": sanitize_untrusted(item.text),
            "source": item.source,
        }
        for item in evidence
    ]

    result.validation_notes = notes

    return result


def no_evidence_result(incident_summary: str) -> Investigation:

    return Investigation(
        incident_summary=incident_summary or "No incident summary available.",
        limitations=[
            "No log evidence, anomaly data or documentation is available "
            "for this incident, so no analysis was attempted."
        ],
        confidence="low",
    )


class InvestigationAgent:

    def __init__(
        self,
        provider: LLMProvider | None,
    ) -> None:
        self.provider = provider

    def investigate(
        self,
        question: str,
        incident_summary: str,
        evidence: list[EvidenceItem],
        valid_incident_ids: set[str] | None = None,
    ) -> InvestigationOutcome:

        if not evidence:
            return InvestigationOutcome(
                ok=True,
                investigation=no_evidence_result(incident_summary),
            )

        if self.provider is None:
            return InvestigationOutcome(
                False,
                error_code=LLMNotConfiguredError.code,
                error_message=LLMNotConfiguredError.user_message,
            )

        prompt = build_investigation_prompt(
            question,
            incident_summary,
            evidence,
        )

        try:
            raw = self.provider.generate_json(
                LLMRequest(
                    system=INVESTIGATION_SYSTEM,
                    prompt=prompt,
                )
            )

            investigation = validate_investigation(
                raw,
                evidence,
                incident_summary,
                valid_incident_ids,
            )

        except LLMError as exc:
            return InvestigationOutcome(
                False,
                error_code=exc.code,
                error_message=exc.user_message,
            )

        return InvestigationOutcome(
            ok=True,
            investigation=investigation,
        )