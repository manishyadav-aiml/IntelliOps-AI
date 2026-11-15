"""Time-window feature engineering.

Causality: every feature of window *t* depends only on events inside window *t* and on counts of
windows *before* t (``error_change``). No future window influences an earlier row.

Definitions (documented in docs/ML_METHODOLOGY.md):
  error_count / warning_count / info_count / critical_count : events of that level in the window
  error_ratio    : (ERROR + CRITICAL) / log_volume
  warning_ratio  : WARNING / log_volume
  unique_templates / repeated_templates : distinct templates / (volume - distinct templates)
  max_service_events / service_count    : busiest service's events / number of services seen
  error_change   : (ERROR+CRITICAL) now minus the previous window (empty windows count as 0)
  mean_seconds_between_errors : mean gap between error events inside the window
                                (window length if fewer than two errors)
"""

import numpy as np
import pandas as pd

FEATURE_NAMES = [
    "info_count",
    "warning_count",
    "error_count",
    "critical_count",
    "error_ratio",
    "warning_ratio",
    "unique_templates",
    "repeated_templates",
    "max_service_events",
    "service_count",
    "log_volume",
    "error_change",
    "mean_seconds_between_errors",
]
MAX_WINDOWS = 200_000
ERROR_LEVELS = ["ERROR", "CRITICAL"]


def build_window_features(frame: pd.DataFrame, window_seconds: int = 60) -> pd.DataFrame:
    """One row per non-empty window, indexed by window start (UTC), plus `affected_service`."""
    columns = [*FEATURE_NAMES, "affected_service"]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    if window_seconds < 1:
        raise ValueError("window_seconds must be >= 1")
    span = (frame["timestamp"].max() - frame["timestamp"].min()).total_seconds()
    if span / window_seconds > MAX_WINDOWS:
        raise ValueError("Time range is too wide for this window size; use a larger window")

    freq = f"{window_seconds}s"
    data = frame.assign(window=frame["timestamp"].dt.floor(freq))
    volume = data.groupby("window").size()
    index = volume.index

    levels = data.groupby(["window", "level"]).size().unstack(fill_value=0)
    for level in ("INFO", "WARNING", "ERROR", "CRITICAL"):
        if level not in levels.columns:
            levels[level] = 0
    levels = levels.reindex(index, fill_value=0)

    feats = pd.DataFrame(index=index)
    feats["info_count"] = levels["INFO"].astype(float)
    feats["warning_count"] = levels["WARNING"].astype(float)
    feats["error_count"] = levels["ERROR"].astype(float)
    feats["critical_count"] = levels["CRITICAL"].astype(float)
    feats["log_volume"] = volume.astype(float)
    error_freq = levels["ERROR"] + levels["CRITICAL"]
    feats["error_ratio"] = error_freq / volume
    feats["warning_ratio"] = levels["WARNING"] / volume
    unique = data.groupby("window")["template"].nunique()
    feats["unique_templates"] = unique.astype(float)
    feats["repeated_templates"] = (volume - unique).astype(float)

    per_service = data.groupby(["window", "service"]).size()
    feats["max_service_events"] = per_service.groupby(level=0).max().astype(float)
    feats["service_count"] = per_service.groupby(level=0).size().astype(float)

    # change vs the previous window on a full grid (past only; gaps count as zero errors)
    grid = pd.date_range(index.min(), index.max(), freq=freq)
    full = error_freq.reindex(grid, fill_value=0).astype(float)
    feats["error_change"] = full.diff().fillna(0.0).reindex(index)

    errors = data[data["level"].isin(ERROR_LEVELS)]
    if errors.empty:
        feats["mean_seconds_between_errors"] = float(window_seconds)
        top_err = pd.Series(dtype=object)
    else:

        def mean_gap(series: pd.Series) -> float:
            ordered = series.sort_values()
            return float(ordered.diff().dt.total_seconds().mean()) if len(ordered) > 1 else np.nan

        gaps = errors.groupby("window")["timestamp"].apply(mean_gap)
        feats["mean_seconds_between_errors"] = gaps.reindex(index).fillna(float(window_seconds))
        err_counts = errors.groupby(["window", "service"]).size()
        top_err = err_counts.groupby(level=0).idxmax().map(lambda pair: pair[1])

    all_counts = per_service
    top_all = all_counts.groupby(level=0).idxmax().map(lambda pair: pair[1])
    feats["affected_service"] = top_err.reindex(index).fillna(top_all).astype(object)
    feats.index.name = "window_start"
    return feats[columns]
