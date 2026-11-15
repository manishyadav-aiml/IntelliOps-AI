"""Benchmark the log parser + template extractor on a file (throughput, templates, parse rate).

    python scripts/benchmark_log_parser.py data/sample_logs/incident_payment_failure.log --miner regex
"""

import _bootstrap  # noqa: F401
import argparse
import time
from pathlib import Path

from app.parsers.drain_parser import create_extractor
from app.parsers.log_parser import ParseStats, iter_records, update_stats
from app.parsers.regex_parser import ParserConfig


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    ap.add_argument("--miner", choices=["drain", "regex"], default="drain")
    args = ap.parse_args()
    extractor = create_extractor(args.miner)
    stats = ParseStats(parser_used=extractor.name)
    start = time.perf_counter()
    messages = []
    for record in iter_records(args.log, ParserConfig()):
        update_stats(stats, record)
        if record.message.strip():
            messages.append(record.message)
    parse_s = time.perf_counter() - start
    start = time.perf_counter()
    for m in messages:
        extractor.learn(m)
    templates = {extractor.extract(m).template_hash for m in messages}
    mine_s = time.perf_counter() - start
    print(
        f"file={args.log.name} miner={extractor.name} entries={stats.entries} structured={stats.structured_entries} "
        f"templates={len(templates)} parse_s={parse_s:.3f} mine_s={mine_s:.3f} "
        f"lines_per_s={stats.entries / max(parse_s + mine_s, 1e-9):.0f}"
    )


if __name__ == "__main__":
    main()
