from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.rag.embeddings import HashingEmbedder
from app.rag.vector_store import VectorStore
from app.services.incident_logic import (
    InvalidTransitionError,
    fingerprint,
    group_anomalous_windows,
    incident_public_id,
    ranges_overlap,
    stats_for_entries,
    validate_transition,
)
from app.services.similarity import find_similar, incident_text, index_metadata, shared

T0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)


def win(minute: int, detected: bool, service: str = "payment", score: float = 5.0):
    start = T0 + timedelta(minutes=minute)
    return SimpleNamespace(
        window_start=start, window_end=start + timedelta(minutes=1), anomaly_detected=detected,
        anomaly_score=score, affected_service=service,
    )


def test_consecutive_anomalous_windows_become_one_incident() -> None:
    cands = group_anomalous_windows([win(10, True), win(11, True), win(12, True), win(13, False)], 60)
    assert len(cands) == 1
    c = cands[0]
    assert c.window_count == 3 and c.start == T0 + timedelta(minutes=10) and c.end == T0 + timedelta(minutes=13)


def test_small_gaps_merge_but_large_gaps_split() -> None:
    merged = group_anomalous_windows([win(10, True), win(13, True)], 60, max_gap_windows=2)
    split = group_anomalous_windows([win(10, True), win(30, True)], 60, max_gap_windows=2)
    assert len(merged) == 1 and len(split) == 2


def test_primary_service_is_the_highest_scoring_and_no_anomalies_means_no_incidents() -> None:
    c = group_anomalous_windows([win(1, True, "db", 3), win(2, True, "payment", 9)], 60)[0]
    assert c.primary_service == "payment" and c.services == ["payment", "db"] and c.max_score == 9
    assert group_anomalous_windows([win(1, False)], 60) == []


def test_fingerprint_is_stable_and_distinguishes_inputs() -> None:
    assert fingerprint(1, 2, "db", T0) == fingerprint(1, 2, "db", T0)
    assert fingerprint(1, 2, "db", T0) != fingerprint(1, 3, "db", T0)
    assert fingerprint(1, 2, "db", T0) != fingerprint(2, 2, "db", T0)


def test_range_overlap_with_grace() -> None:
    g = timedelta(minutes=2)
    assert ranges_overlap(T0, T0 + timedelta(minutes=5), T0 + timedelta(minutes=6), T0 + timedelta(minutes=9), g)
    assert not ranges_overlap(T0, T0 + timedelta(minutes=5), T0 + timedelta(minutes=30), T0 + timedelta(minutes=40), g)


@pytest.mark.parametrize(("old", "new"), [("OPEN", "INVESTIGATING"), ("INVESTIGATING", "MITIGATED"),
                                          ("MITIGATED", "RESOLVED"), ("RESOLVED", "OPEN"), ("OPEN", "OPEN")])
def test_valid_transitions(old: str, new: str) -> None:
    validate_transition(old, new)


@pytest.mark.parametrize(("old", "new"), [("MITIGATED", "OPEN"), ("RESOLVED", "MITIGATED"), ("OPEN", "BOGUS")])
def test_invalid_transitions(old: str, new: str) -> None:
    with pytest.raises(InvalidTransitionError):
        validate_transition(old, new)


def test_stats_for_entries() -> None:
    s = stats_for_entries([("INFO", "api"), ("ERROR", "db"), ("CRITICAL", "db"), ("WARNING", "unknown"), ("ERROR", "pay")])
    assert (s.total_events, s.error_count, s.critical_count, s.warning_count) == (5, 3, 1, 1)
    assert s.error_services[0] == "db" and "unknown" not in s.services


def test_public_id_format() -> None:
    assert incident_public_id(1) == "INC-1001"


def build_index():
    e = HashingEmbedder()
    store = VectorStore(e.dim, e.name)
    rows = [
        ("INC-1001", 1, "Payment gateway timeouts", ["payment-service", "db"], ["Payment <*> failed: gateway timeout"], ["Payment <*> failed: gateway timeout"]),
        ("INC-1002", 1, "Login failures burst", ["auth-service"], ["Authentication failed for user <*>"], ["Authentication failed for user <*>"]),
        ("INC-1003", 2, "Payment gateway timeouts", ["payment-service"], ["Payment <*> failed: gateway timeout"], ["Payment <*> failed: gateway timeout"]),
    ]
    for iid, owner, title, svc, tpl, err in rows:
        text = incident_text(title, svc[0], "P2", tpl, [])
        store.add([iid], e.embed([text]), [index_metadata(owner, iid, title, svc, tpl, err)])
    return store, e


def test_similar_incident_retrieval_reports_shared_items_and_isolates_users() -> None:
    store, e = build_index()
    text = incident_text("Payment gateway timeouts again", "payment-service", "P2", ["Payment <*> failed: gateway timeout"], [])
    result = find_similar(store, e, 1, "NEW-1", text, ["payment-service"], ["Payment <*> failed: gateway timeout"],
                          ["Payment <*> failed: gateway timeout"], min_score=0.2)
    assert [r.similar_incident_id for r in result][0] == "INC-1001"
    assert "INC-1003" not in [r.similar_incident_id for r in result]  # other user's incident never returned
    assert result[0].shared_services == ["payment-service"] and result[0].shared_templates
    assert "not a confirmed common root cause" in result[0].note


def test_similar_excludes_itself_and_handles_empty_input() -> None:
    store, e = build_index()
    text = incident_text("Payment gateway timeouts", "payment-service", "P2", ["Payment <*> failed: gateway timeout"], [])
    assert "INC-1001" not in [r.similar_incident_id for r in find_similar(store, e, 1, "INC-1001", text, [], [], [], min_score=0.1)]
    assert find_similar(store, e, 1, "X", "   ", [], [], []) == []
    assert shared(["a", "b", "a"], ["a"]) == ["a"]
