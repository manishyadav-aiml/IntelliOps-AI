"""Reproducible block-level evaluation (Isolation Forest vs Local Outlier Factor).

    python scripts/evaluate_models.py --mode synthetic        # pipeline check on SYNTHETIC data
    python scripts/evaluate_models.py --mode hdfs --counts data/processed/hdfs_block_counts.csv \
                                      --labels data/processed/hdfs_block_labels.csv

Results are printed and written to experiments/results/<mode>.json. Synthetic results validate
the code path only; they say nothing about performance on LogHub or real logs.
"""

import _bootstrap  # noqa: F401
import argparse
import json
from pathlib import Path

import pandas as pd

from app.ml.experiments import run_block_experiment
from app.ml.hdfs import load_labels, make_synthetic_blocks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["synthetic", "hdfs"], default="synthetic")
    ap.add_argument("--counts", type=Path)
    ap.add_argument("--labels", type=Path)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quantile", type=float, default=0.95)
    ap.add_argument("--out", type=Path, default=Path("experiments/results"))
    args = ap.parse_args()

    if args.mode == "synthetic":
        counts, labels = make_synthetic_blocks(n_blocks=2000, anomaly_rate=0.05, seed=args.seed)
        note = "SYNTHETIC data - validates the pipeline only"
    else:
        if not (args.counts and args.labels):
            ap.error("--counts and --labels are required for --mode hdfs")
        counts = pd.read_csv(args.counts, index_col=0)
        label_map = load_labels(args.labels) if args.labels.suffix == ".csv" and "Label" in args.labels.read_text()[:50] else {}
        labels = counts.index.map(lambda b: label_map.get(b, 0)).to_numpy()
        note = "LogHub HDFS (as prepared by scripts/prepare_dataset.py)"
    result = run_block_experiment(counts, labels, seed=args.seed, threshold_quantile=args.quantile)
    result["data"] = note
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"{args.mode}.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
