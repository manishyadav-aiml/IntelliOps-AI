"""Evaluation helpers. Only labelled data can produce precision/recall; nothing here invents numbers."""

from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit


def split_by_group(groups: Any, test_size: float = 0.3, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """Train/test indices such that no group (e.g. HDFS block id) appears on both sides."""
    groups = np.asarray(groups)
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train, test = next(splitter.split(np.zeros(len(groups)), groups=groups))
    assert not set(groups[train]) & set(groups[test])
    return train, test


def binary_metrics(y_true: Any, scores: Any, threshold: float) -> dict[str, Any]:
    y = np.asarray(y_true).astype(int)
    s = np.asarray(scores, dtype=float)
    pred = (s >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    both_classes = len(set(y.tolist())) == 2
    return {
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "pr_auc": float(average_precision_score(y, s)) if both_classes else None,
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "threshold": float(threshold),
        "n": int(len(y)),
        "n_positive": int(y.sum()),
    }
