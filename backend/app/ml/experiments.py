"""Block-level anomaly experiments (IF vs LOF) with leakage-free splitting.

How labels and thresholds are used (unsupervised models):
  * Models are fitted WITHOUT labels on the train split.
  * The decision threshold is a quantile of the TRAIN scores (`threshold_quantile`), never tuned on test labels.
  * Labels are used only afterwards, on the test split, to compute metrics.
  * The vocabulary and scaler come from the train split only.
"""

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

from app.ml.evaluation import binary_metrics, split_by_group
from app.ml.hdfs import project_columns


def run_block_experiment(
    counts: pd.DataFrame, labels: np.ndarray, seed: int = 42, test_size: float = 0.3,
    threshold_quantile: float = 0.95,
) -> dict[str, Any]:
    labels = np.asarray(labels).astype(int)
    train_idx, test_idx = split_by_group(counts.index.to_numpy(), test_size, seed)
    columns = list(counts.columns)  # NOTE: callers must pass train-vocabulary columns only if known earlier
    train_x = np.log1p(counts.iloc[train_idx][columns])
    test_x = np.log1p(project_columns(counts.iloc[test_idx], columns))
    scaler = StandardScaler().fit(train_x)
    tr, te = scaler.transform(train_x), scaler.transform(test_x)

    models: dict[str, Any] = {
        "isolation_forest": IsolationForest(n_estimators=200, random_state=seed).fit(tr),
        "local_outlier_factor": LocalOutlierFactor(n_neighbors=min(20, len(tr) - 1), novelty=True).fit(tr),
    }
    results: dict[str, Any] = {
        "seed": seed,
        "test_size": test_size,
        "threshold_quantile": threshold_quantile,
        "n_train_blocks": int(len(train_idx)),
        "n_test_blocks": int(len(test_idx)),
        "test_anomaly_rate": float(labels[test_idx].mean()),
        "models": {},
    }
    for name, model in models.items():
        threshold = float(np.quantile(-model.score_samples(tr), threshold_quantile))
        results["models"][name] = binary_metrics(labels[test_idx], -model.score_samples(te), threshold)
    return results
