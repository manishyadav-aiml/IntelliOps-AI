from pathlib import Path

import pytest

from app.ml.anomaly_detection import (
    BaselineDetector,
    IsolationForestModel,
    LocalOutlierFactorModel,
    ModelTrainingError,
    detect_anomalies,
    load_latest_model,
    save_model,
)
from app.ml.feature_engineering import build_window_features
from app.ml.preprocessing import prepare_frame
from datetime import timedelta

from app.ml.preprocessing import LogRow
from tests.helpers import T0, traffic_rows


def feats(burst: int | None, minutes: int = 60, seed: int = 1):
    return build_window_features(prepare_frame(traffic_rows(minutes, burst, seed))[0], 60)


def train_feats_with_past_bursts(seed: int = 3):
    """120 min of traffic containing two earlier bursts (minutes 20 and 80)."""
    rows = traffic_rows(120, burst_minute=20, seed=seed)
    extra = [
        LogRow(r.timestamp + timedelta(minutes=60), r.level, r.service, r.template)
        for r in rows
        if r.level in ("ERROR", "CRITICAL") and r.service == "payment-service" and 20 <= (r.timestamp - T0).seconds // 60 <= 21
    ]
    return build_window_features(prepare_frame(rows + extra)[0], 60)


def test_baseline_flags_the_burst_and_not_stable_traffic() -> None:
    results = BaselineDetector().detect(feats(burst=40))
    flagged = {r.window_start.minute + 60 * (r.window_start.hour - 9) for r in results if r.anomaly_detected}
    assert flagged & {40, 41}
    assert len(flagged) <= 4
    assert not any(r.anomaly_detected for r in BaselineDetector().detect(feats(burst=None, seed=1)))


def test_baseline_does_not_score_before_min_history_and_uses_only_the_past() -> None:
    early = BaselineDetector(min_history=5).detect(feats(burst=40))[:5]
    assert all(r.anomaly_score == 0.0 and not r.anomaly_detected for r in early)
    short = BaselineDetector().detect(feats(burst=40, minutes=45))
    full = BaselineDetector().detect(feats(burst=40, minutes=60))
    assert [r.anomaly_score for r in short[:44]] == [r.anomaly_score for r in full[:44]]


def test_result_fields_are_complete_and_explained() -> None:
    result = [r for r in BaselineDetector().detect(feats(burst=40)) if r.anomaly_detected][0]
    assert result.affected_service == "payment-service"
    assert result.model_version == "baseline-v1" and result.threshold == 3.5
    assert result.contributing_features and "name" in result.contributing_features[0]
    assert result.window_end > result.window_start and result.detection_timestamp is not None


def test_isolation_forest_detects_burst_when_training_data_contains_bursts() -> None:
    model = IsolationForestModel().fit(train_feats_with_past_bursts(), threshold_quantile=0.97)
    results = model.detect(feats(burst=30, minutes=60, seed=4))
    flagged = [r.window_start.minute for r in results if r.anomaly_detected]
    assert set(flagged) == {30, 31}
    top = max(results, key=lambda r: r.anomaly_score)
    assert top.model_version.startswith("isolation_forest-") and top.method == "isolation_forest"
    assert top.contributing_features and top.affected_service == "payment-service"


def test_known_limitation_isolation_forest_alone_misses_burst_after_quiet_training() -> None:
    """Regression test documenting that Isolation Forest does not extrapolate beyond its training range."""
    model = IsolationForestModel().fit(feats(burst=None, minutes=120, seed=3))
    results = model.detect(feats(burst=30, minutes=60, seed=4))
    assert not any(r.anomaly_detected and r.window_start.minute in (30, 31) for r in results)


def test_baseline_safeguard_rescues_the_burst_after_quiet_training(tmp_path: Path) -> None:
    save_model(IsolationForestModel().fit(feats(burst=None, minutes=120, seed=3)), tmp_path)
    results, method = detect_anomalies(feats(burst=30, minutes=60, seed=4), 60, tmp_path)
    assert "baseline safeguard" in method
    rescued = [r for r in results if r.anomaly_detected and r.window_start.minute in (30, 31)]
    assert rescued and all(r.method == "baseline_robust_zscore" for r in rescued)


def test_training_requires_enough_windows() -> None:
    with pytest.raises(ModelTrainingError):
        IsolationForestModel().fit(feats(burst=None, minutes=10))


def test_model_save_load_roundtrip_and_versioning(tmp_path: Path) -> None:
    model = IsolationForestModel().fit(feats(burst=None, minutes=60, seed=5))
    path = save_model(model, tmp_path)
    assert path.exists() and (tmp_path / "latest.json").exists()
    loaded = load_latest_model(tmp_path)
    assert loaded is not None and loaded.version == model.version
    test = feats(burst=20, minutes=40, seed=6)
    assert [r.anomaly_score for r in loaded.detect(test)] == [r.anomaly_score for r in model.detect(test)]
    assert load_latest_model(tmp_path / "missing") is None


def test_threshold_override_changes_detections() -> None:
    model = IsolationForestModel().fit(feats(burst=None, minutes=60, seed=7))
    test = feats(burst=20, minutes=40, seed=8)
    assert not any(r.anomaly_detected for r in model.detect(test, threshold=10.0))
    assert all(r.anomaly_detected for r in model.detect(test, threshold=0.0))


def test_lof_comparison_model_works() -> None:
    model = LocalOutlierFactorModel().fit(feats(burst=None, minutes=60, seed=9))
    results = model.detect(feats(burst=25, minutes=40, seed=10))
    assert max(results, key=lambda r: r.anomaly_score).window_start.minute in (25, 26)


def test_detect_anomalies_falls_back_to_baseline_without_a_model(tmp_path: Path) -> None:
    results, method = detect_anomalies(feats(burst=40), 60, tmp_path)
    assert "baseline" in method and results[0].model_version == "baseline-v1"


def test_detect_anomalies_uses_matching_trained_model_only(tmp_path: Path) -> None:
    save_model(IsolationForestModel().fit(feats(burst=None, minutes=60, seed=11)), tmp_path)
    _, method = detect_anomalies(feats(burst=20, minutes=40), 60, tmp_path)
    assert method.startswith("isolation_forest")
    _, other = detect_anomalies(feats(burst=20, minutes=40), 300, tmp_path)  # window mismatch
    assert "baseline" in other


def test_empty_features_give_no_results() -> None:
    results, method = detect_anomalies(feats(burst=None, minutes=0), 60)
    assert results == [] and "no timestamped" in method
