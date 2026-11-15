"""HDFS block-level utilities (LogHub HDFS) and a clearly-labelled SYNTHETIC generator.

HDFS anomaly labels are per block id, so evaluation splits on block ids (never on single lines).
The vocabulary (columns) is fixed from the TRAIN split; test blocks are projected onto it, so no
test information leaks into preprocessing.
"""

import csv
import re
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd

BLOCK_RE = re.compile(r"blk_-?\d+")


def extract_block_ids(message: str) -> list[str]:
    return sorted(set(BLOCK_RE.findall(message)))


def build_block_counts(items: Iterable[tuple[str, str]]) -> pd.DataFrame:
    """items = (message, template_hash). Returns blocks x templates event-count matrix."""
    counts: dict[str, dict[str, int]] = {}
    for message, template in items:
        for block in extract_block_ids(message):
            counts.setdefault(block, {}).setdefault(template, 0)
            counts[block][template] += 1
    return pd.DataFrame.from_dict(counts, orient="index").fillna(0).astype(float).sort_index()


def project_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Reindex to the train vocabulary (unknown templates dropped, missing ones zero)."""
    return frame.reindex(columns=columns, fill_value=0.0)


def load_labels(path: Path) -> dict[str, int]:
    """LogHub `anomaly_label.csv` (BlockId,Label with Normal/Anomaly) -> {block: 0/1}."""
    labels = {}
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            labels[row["BlockId"]] = 1 if row["Label"].strip().lower() == "anomaly" else 0
    return labels


def make_synthetic_blocks(n_blocks: int = 600, anomaly_rate: float = 0.08, seed: int = 7) -> tuple[pd.DataFrame, np.ndarray]:
    """SYNTHETIC block x template counts with injected anomalies. NOT LogHub data."""
    rng = np.random.default_rng(seed)
    normal_templates = [f"t_normal_{i}" for i in range(8)]
    rare_templates = [f"t_rare_{i}" for i in range(4)]
    rows, labels = [], []
    for i in range(n_blocks):
        anomalous = rng.random() < anomaly_rate
        row = {t: float(rng.poisson(3)) for t in normal_templates}
        row["t_normal_0"] = max(row["t_normal_0"], 1.0)
        if anomalous:
            for t in rng.choice(rare_templates, size=rng.integers(1, 3), replace=False):
                row[str(t)] = float(rng.integers(2, 6))
            row["t_normal_1"] = float(rng.poisson(10))
        rows.append(row)
        labels.append(int(anomalous))
    frame = pd.DataFrame(rows).fillna(0.0)
    frame.index = [f"blk_{100000 + i}" for i in range(n_blocks)]
    return frame, np.asarray(labels)
