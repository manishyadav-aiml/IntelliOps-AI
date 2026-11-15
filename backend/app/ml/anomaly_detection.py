"""Anomaly detection over window features.

Methods
  * BaselineDetector        - no training needed; causal robust z-score vs earlier windows.
  * IsolationForestModel    - primary ML model (scaler + IsolationForest), persisted with joblib.
  * LocalOutlierFactorModel - comparison model (novelty=True so it can score unseen data).

`anomaly_score` is a model-specific score, NOT a probability (it is uncalibrated). Larger means
more anomalous. Baseline scores are robust z-values; Isolation Forest scores are -score_samples.

Security: joblib files are pickles. Only load model files from a directory you control.
"""

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

from app.ml.feature_engineering import FEATURE_NAMES

MIN_TRAIN_WINDOWS = 20
BASELINE_KEYS = ["error_count", "critical_count", "error_ratio", "log_volume"]


class ModelTrainingError(ValueError):
    """Not enough / unusable data to train a model."""


@dataclass
class AnomalyResult:
    window_start: datetime
    window_end: datetime
    anomaly_detected: bool
    anomaly_score: float  # uncalibrated; not a probability
    threshold: float
    contributing_features: list[dict[str, Any]]
    affected_service: str
    detection_timestamp: datetime
    model_version: str
    method: str
    features: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _to_py(ts: pd.Timestamp) -> datetime:
    return ts.to_pydatetime()


def _contributors(z_row: pd.Series, k: int = 3) -> list[dict[str, Any]]:
    """Top-k features by absolute z-score (positive deviations first on ties)."""
    ordered = z_row.reindex(z_row.abs().sort_values(ascending=False).index).head(k)
    return [{"name": name, "z_score": round(float(z), 3)} for name, z in ordered.items() if abs(z) > 0]


class BaselineDetector:
    """Expanding-window robust z-score. Window i is compared only with windows before i."""

    version = "baseline-v1"

    def __init__(self, window_seconds: int = 60, min_history: int = 5, z_threshold: float = 3.5) -> None:
        self.window_seconds = window_seconds
        self.min_history = min_history
        self.z_threshold = z_threshold

    def detect(self, feats: pd.DataFrame) -> list[AnomalyResult]:
        results: list[AnomalyResult] = []
        now = datetime.now(UTC)
        values = feats[BASELINE_KEYS].astype(float)
        for i, (start, row) in enumerate(feats.iterrows()):
            z_values: dict[str, float] = {}
            if i >= self.min_history:
                history = values.iloc[:i]
                for key in BASELINE_KEYS:
                    median = float(history[key].median())
                    mad = float((history[key] - median).abs().median())
                    floor = 0.05 if key == "error_ratio" else 1.0
                    scale = max(1.4826 * mad, floor)
                    z_values[key] = (float(row[key]) - median) / scale
            upward = {k: v for k, v in z_values.items() if v > 0}
            score = max(upward.values()) if upward else 0.0
            contributors = [
                {"name": k, "z_score": round(v, 3)}
                for k, v in sorted(upward.items(), key=lambda kv: kv[1], reverse=True)[:3]
                if v >= 1
            ]
            results.append(
                AnomalyResult(
                    window_start=_to_py(start),
                    window_end=_to_py(start) + timedelta(seconds=self.window_seconds),
                    anomaly_detected=score >= self.z_threshold,
                    anomaly_score=round(float(score), 4),
                    threshold=self.z_threshold,
                    contributing_features=contributors,
                    affected_service=str(row["affected_service"]),
                    detection_timestamp=now,
                    model_version=self.version,
                    method="baseline_robust_zscore",
                    features={k: float(row[k]) for k in FEATURE_NAMES},
                )
            )
        return results


class _SklearnWindowModel:
    method = "base"

    def __init__(self, window_seconds: int = 60) -> None:
        self.window_seconds = window_seconds
        self.feature_names = list(FEATURE_NAMES)
        self.scaler: StandardScaler | None = None
        self.model: Any = None
        self.threshold: float = 0.5
        self.version = "untrained"
        self.trained_at: str | None = None
        self.n_train = 0
        self.train_mean: dict[str, float] = {}
        self.train_std: dict[str, float] = {}

    def _build(self) -> Any:  # pragma: no cover - overridden
        raise NotImplementedError

    def fit(self, feats: pd.DataFrame, threshold_quantile: float = 0.99) -> "_SklearnWindowModel":
        if len(feats) < MIN_TRAIN_WINDOWS:
            raise ModelTrainingError(
                f"Need at least {MIN_TRAIN_WINDOWS} windows to train, got {len(feats)}"
            )
        x = feats[self.feature_names].astype(float).to_numpy()
        self.scaler = StandardScaler().fit(x)
        scaled = self.scaler.transform(x)
        self.model = self._build().fit(scaled)
        scores = self._score_scaled(scaled)
        self.threshold = float(np.quantile(scores, threshold_quantile))
        self.n_train = len(feats)
        self.trained_at = datetime.now(UTC).isoformat()
        self.train_mean = dict(zip(self.feature_names, self.scaler.mean_.tolist(), strict=True))
        self.train_std = dict(zip(self.feature_names, self.scaler.scale_.tolist(), strict=True))
        digest = hashlib.sha1(f"{self.method}|{self.n_train}|{self.trained_at}".encode()).hexdigest()[:8]  # noqa: S324
        self.version = f"{self.method}-{digest}"
        return self

    def _score_scaled(self, scaled: np.ndarray) -> np.ndarray:
        return -self.model.score_samples(scaled)

    def score(self, feats: pd.DataFrame) -> np.ndarray:
        if self.model is None or self.scaler is None:
            raise ModelTrainingError("Model is not trained")
        x = feats[self.feature_names].astype(float).to_numpy()
        return self._score_scaled(self.scaler.transform(x))

    def detect(self, feats: pd.DataFrame, threshold: float | None = None) -> list[AnomalyResult]:
        limit = self.threshold if threshold is None else threshold
        scores = self.score(feats)
        scaled = pd.DataFrame(
            self.scaler.transform(feats[self.feature_names].astype(float).to_numpy()),  # type: ignore[union-attr]
            index=feats.index,
            columns=self.feature_names,
        )
        now = datetime.now(UTC)
        out: list[AnomalyResult] = []
        for (start, row), score, (_, z_row) in zip(feats.iterrows(), scores, scaled.iterrows(), strict=True):
            out.append(
                AnomalyResult(
                    window_start=_to_py(start),
                    window_end=_to_py(start) + timedelta(seconds=self.window_seconds),
                    anomaly_detected=bool(score >= limit),
                    anomaly_score=round(float(score), 4),
                    threshold=round(float(limit), 4),
                    contributing_features=_contributors(z_row),
                    affected_service=str(row["affected_service"]),
                    detection_timestamp=now,
                    model_version=self.version,
                    method=self.method,
                    features={k: float(row[k]) for k in self.feature_names},
                )
            )
        return out

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @staticmethod
    def load(path: Path) -> "_SklearnWindowModel":
        model = joblib.load(path)  # only load files from a trusted directory
        if not isinstance(model, _SklearnWindowModel):
            raise ValueError("Not an IntelliOps anomaly model file")
        return model


class IsolationForestModel(_SklearnWindowModel):
    method = "isolation_forest"

    def __init__(self, window_seconds: int = 60, n_estimators: int = 200, contamination: float | str = "auto",
                 random_state: int = 42) -> None:
        super().__init__(window_seconds)
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state

    def _build(self) -> IsolationForest:
        return IsolationForest(
            n_estimators=self.n_estimators, contamination=self.contamination, random_state=self.random_state
        )


class LocalOutlierFactorModel(_SklearnWindowModel):
    """Comparison model. novelty=True is required to score data not seen during fit."""

    method = "local_outlier_factor"

    def __init__(self, window_seconds: int = 60, n_neighbors: int = 20) -> None:
        super().__init__(window_seconds)
        self.n_neighbors = n_neighbors

    def _build(self) -> LocalOutlierFactor:
        return LocalOutlierFactor(n_neighbors=self.n_neighbors, novelty=True)

    def _score_scaled(self, scaled: np.ndarray) -> np.ndarray:
        # LOF's training scores via score_samples (novelty mode) are optimistic for training points;
        # the threshold is therefore a training-set quantile and should be read with that caveat.
        return -self.model.score_samples(scaled)

    def fit(self, feats: pd.DataFrame, threshold_quantile: float = 0.99) -> "LocalOutlierFactorModel":
        self.n_neighbors = max(1, min(self.n_neighbors, len(feats) - 1))
        super().fit(feats, threshold_quantile)
        return self


# ---- persistence / registry ----
def save_model(model: _SklearnWindowModel, models_dir: Path) -> Path:
    path = models_dir / f"anomaly_{model.version}.joblib"
    model.save(path)
    (models_dir / "latest.json").write_text(
        '{"file": "%s", "version": "%s", "method": "%s", "trained_at": "%s", "n_train": %d}\n'
        % (path.name, model.version, model.method, model.trained_at, model.n_train)
    )
    return path


def load_latest_model(models_dir: Path) -> _SklearnWindowModel | None:
    import json

    pointer = models_dir / "latest.json"
    if not pointer.exists():
        return None
    meta = json.loads(pointer.read_text())
    file = models_dir / Path(meta["file"]).name  # never follow paths out of models_dir
    return _SklearnWindowModel.load(file) if file.exists() else None


def detect_anomalies(
    feats: pd.DataFrame, window_seconds: int, models_dir: Path | None = None,
    threshold_override: float | None = None,
) -> tuple[list[AnomalyResult], str]:
    """Use the latest trained model if it matches the requested window; otherwise the baseline.

    Known limitation of Isolation Forest: it cannot score a window as more anomalous than the most
    extreme window seen in training (it does not extrapolate). A model trained only on quiet
    traffic can therefore miss a large burst. When a trained model is used, windows it does not
    flag are also checked by the causal baseline; baseline detections are kept as separate
    results labelled `baseline_robust_zscore`, so the origin of every detection stays visible.

    Returns (results, method_description).
    """
    if feats.empty:
        return [], "none (no timestamped log entries)"
    baseline = BaselineDetector(window_seconds).detect(feats)
    if models_dir is not None:
        model = load_latest_model(models_dir)
        if model is not None and model.window_seconds == window_seconds and model.feature_names == FEATURE_NAMES:
            ml_results = model.detect(feats, threshold_override)
            merged = [
                base if (not ml.anomaly_detected and base.anomaly_detected) else ml
                for ml, base in zip(ml_results, baseline, strict=True)
            ]
            return merged, f"{model.method} ({model.version}) + baseline safeguard"
    return baseline, "baseline_robust_zscore (no trained model)"
