"""Turn parsed log rows into a clean time-indexed DataFrame for feature engineering."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

FRAME_COLUMNS = ["timestamp", "level", "service", "template"]


@dataclass(frozen=True)
class LogRow:
    timestamp: datetime | None
    level: str
    service: str
    template: str  # template hash


def prepare_frame(rows: Iterable[LogRow]) -> tuple[pd.DataFrame, int]:
    """Return (frame, dropped_without_timestamp).

    Rows without a timestamp cannot be placed in a time window, so they are excluded from
    anomaly detection (and counted, so callers can report it) rather than guessed.
    """
    kept, dropped = [], 0
    for row in rows:
        if row.timestamp is None:
            dropped += 1
            continue
        kept.append((row.timestamp, row.level, row.service, row.template))
    frame = pd.DataFrame(kept, columns=FRAME_COLUMNS)
    if not frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame = frame.sort_values("timestamp", kind="stable").reset_index(drop=True)
    return frame, dropped
