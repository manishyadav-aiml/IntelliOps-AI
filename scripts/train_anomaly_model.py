"""Train and save a window-level Isolation Forest from one or more log files.

    python scripts/train_anomaly_model.py --logs data/sample_logs/normal_activity.log --window 60

NOTE: the bundled sample logs are SYNTHETIC; a model trained on them is for demonstration only.
Train on logs that resemble the logs you want to monitor, ideally including some past incidents
(Isolation Forest cannot rate a window as more anomalous than the most extreme one it has seen).
"""

import _bootstrap  # noqa: F401
import argparse
from pathlib import Path

from app.ml.anomaly_detection import IsolationForestModel, save_model
from app.ml.feature_engineering import build_window_features
from app.ml.preprocessing import LogRow, prepare_frame
from app.parsers.drain_parser import create_extractor
from app.parsers.log_parser import iter_records
from app.parsers.regex_parser import ParserConfig


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", type=Path, nargs="+", required=True)
    ap.add_argument("--window", type=int, default=60)
    ap.add_argument("--quantile", type=float, default=0.99, help="train-score quantile used as threshold")
    ap.add_argument("--models-dir", type=Path, default=Path("models"))
    ap.add_argument("--miner", choices=["drain", "regex"], default="regex")
    args = ap.parse_args()

    records = [r for path in args.logs for r in iter_records(path, ParserConfig()) if r.message.strip()]
    extractor = create_extractor(args.miner)
    for r in records:
        extractor.learn(r.message)
    rows = [LogRow(r.timestamp, r.level, r.service, extractor.extract(r.message).template_hash) for r in records]
    frame, dropped = prepare_frame(rows)
    feats = build_window_features(frame, args.window)
    print(f"{len(records)} entries, {dropped} without timestamp, {len(feats)} windows of {args.window}s")
    model = IsolationForestModel(window_seconds=args.window).fit(feats, args.quantile)
    path = save_model(model, args.models_dir)
    print(f"Saved {path}  version={model.version}  threshold={model.threshold:.4f} (score is not a probability)")


if __name__ == "__main__":
    main()
