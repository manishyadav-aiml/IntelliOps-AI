# Dataset guide (LogHub)

Source: https://github.com/logpai/loghub (repository: `https://github.com/logpai/loghub.git`).

**Status: no dataset has been downloaded, prepared or evaluated yet.** The scripts (`scripts/download_dataset.py`, `prepare_dataset.py`, ...) arrive in Phase 3. No evaluation results exist.

## Manual acquisition
```bash
mkdir -p data/raw && cd data/raw
git clone --depth 1 https://github.com/logpai/loghub.git
```
The LogHub repository holds small 2k-line samples per system; the full datasets (e.g. HDFS_v1, BGL) are linked from its README (Zenodo). Download full archives manually; do not fetch them at application startup. `data/raw/` is git-ignored.

## Licensing and use
Check the LogHub README and each dataset's terms before use. LogHub is intended for research/academic use; cite the LogHub papers listed in its README in your report.

## Planned evaluation rules (implemented in Phase 3)
- HDFS: split by block ID, never by individual log line.
- No preprocessing/oversampling fitted on test data.
- Report only metrics actually produced by `scripts/evaluate_models.py`.

## Scripts (written; LogHub runs not performed)
| Script | Purpose |
|--------|---------|
| `scripts/download_dataset.py` | prints instructions; `--clone` shallow-clones the LogHub repo into `data/raw/loghub` (manual only, never at startup) |
| `scripts/prepare_dataset.py` | raw HDFS log + `BlockId,Label` CSV -> `data/processed/hdfs_block_counts.csv` / `hdfs_block_labels.csv` |
| `scripts/train_anomaly_model.py` | window-level Isolation Forest from log files |
| `scripts/evaluate_models.py` | IF vs LOF with a block-id split; `--mode synthetic` (pipeline check) or `--mode hdfs` |
| `scripts/benchmark_log_parser.py` | parser/miner throughput and template counts |
| `scripts/generate_sample_logs.py` | deterministic synthetic samples |

Reproduce: `python scripts/prepare_dataset.py --log <HDFS.log> --labels <anomaly_label.csv>` then `python scripts/evaluate_models.py --mode hdfs --counts data/processed/hdfs_block_counts.csv --labels data/processed/hdfs_block_labels.csv`.
File names/locations inside LogHub and Zenodo must be checked against their READMEs; they were not verified. Cite LogHub in any report. BGL, OpenStack and Apache are **not** covered by a prepared pipeline yet (their labelling differs from HDFS).
