"""Prepare HDFS block-level count matrices from a raw HDFS log + LogHub label file.

    python scripts/prepare_dataset.py --log data/raw/HDFS.log --labels data/raw/anomaly_label.csv

Writes data/processed/hdfs_block_counts.csv and hdfs_block_labels.csv (git-ignored).
The log is streamed line by line. Exact LogHub file names/locations must be checked against the
LogHub README; this script only needs a raw HDFS log and the `BlockId,Label` CSV.
"""

import _bootstrap  # noqa: F401  (adds backend/ to sys.path)
import argparse
import csv
from pathlib import Path

from app.ml.hdfs import build_block_counts, load_labels
from app.parsers.drain_parser import create_extractor
from app.parsers.log_parser import iter_records
from app.parsers.regex_parser import ParserConfig


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("data/processed"))
    ap.add_argument("--miner", choices=["drain", "regex"], default="drain")
    args = ap.parse_args()

    config = ParserConfig()
    extractor = create_extractor(args.miner)
    print(f"Template miner: {extractor.name}")
    messages = [r.message for r in iter_records(args.log, config) if r.message.strip()]
    for message in messages:
        extractor.learn(message)
    counts = build_block_counts((m, extractor.extract(m).template_hash) for m in messages)
    labels = load_labels(args.labels)
    common = [b for b in counts.index if b in labels]
    counts = counts.loc[common]
    args.out.mkdir(parents=True, exist_ok=True)
    counts.to_csv(args.out / "hdfs_block_counts.csv")
    with open(args.out / "hdfs_block_labels.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["BlockId", "Label"])
        writer.writerows((b, labels[b]) for b in common)
    print(f"Blocks: {len(common)}  anomalies: {sum(labels[b] for b in common)}  templates: {counts.shape[1]}")


if __name__ == "__main__":
    main()
