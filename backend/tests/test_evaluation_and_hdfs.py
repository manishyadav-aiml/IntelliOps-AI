import numpy as np
import pytest

from app.ml.evaluation import binary_metrics, split_by_group
from app.ml.hdfs import (
    build_block_counts,
    extract_block_ids,
    load_labels,
    make_synthetic_blocks,
    project_columns,
)


def test_binary_metrics_known_example() -> None:
    m = binary_metrics([0, 0, 0, 0, 1, 1], [0.1, 0.2, 0.9, 0.3, 0.8, 0.4], threshold=0.5)
    assert m["confusion_matrix"] == {"tn": 3, "fp": 1, "fn": 1, "tp": 1}
    assert m["precision"] == pytest.approx(0.5) and m["recall"] == pytest.approx(0.5)
    assert m["false_positive_rate"] == pytest.approx(0.25)
    assert 0.0 < m["pr_auc"] <= 1.0


def test_metrics_with_single_class_report_no_pr_auc() -> None:
    assert binary_metrics([0, 0, 0], [0.1, 0.2, 0.3], 0.5)["pr_auc"] is None


def test_group_split_never_shares_a_group() -> None:
    groups = np.repeat([f"blk_{i}" for i in range(50)], 4)  # 4 lines per block
    train, test = split_by_group(groups, 0.3, seed=1)
    assert not set(groups[train]) & set(groups[test])
    assert len(train) + len(test) == len(groups)


def test_block_id_extraction_and_counts() -> None:
    assert extract_block_ids("Receiving block blk_-123 src: /10.0.0.1 dest blk_456") == ["blk_-123", "blk_456"]
    counts = build_block_counts([("x blk_1 a", "t1"), ("y blk_1 b", "t1"), ("z blk_2", "t2")])
    assert counts.loc["blk_1", "t1"] == 2 and counts.loc["blk_2", "t2"] == 1


def test_project_columns_uses_train_vocabulary_only() -> None:
    counts = build_block_counts([("blk_1", "t1"), ("blk_2", "t_new")])
    projected = project_columns(counts, ["t1", "t2"])
    assert list(projected.columns) == ["t1", "t2"] and projected.loc["blk_2"].sum() == 0


def test_load_labels(tmp_path) -> None:
    path = tmp_path / "labels.csv"
    path.write_text("BlockId,Label\nblk_1,Normal\nblk_2,Anomaly\n")
    assert load_labels(path) == {"blk_1": 0, "blk_2": 1}


def test_synthetic_block_experiment_beats_chance_with_block_split() -> None:
    """Synthetic data only: demonstrates the pipeline, says nothing about LogHub performance."""
    from app.ml.experiments import run_block_experiment

    counts, labels = make_synthetic_blocks(n_blocks=800, anomaly_rate=0.08, seed=7)
    result = run_block_experiment(counts, labels, seed=7, threshold_quantile=0.92)
    assert result["n_train_blocks"] + result["n_test_blocks"] == 800
    for name in ("isolation_forest", "local_outlier_factor"):
        assert result["models"][name]["pr_auc"] > 3 * result["test_anomaly_rate"], name
