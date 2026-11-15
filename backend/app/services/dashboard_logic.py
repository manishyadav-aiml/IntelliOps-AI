"""Pure aggregation helpers for the dashboard (all inputs come from the database; nothing is made up)."""

from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timedelta


def bucket_start(ts: datetime, bucket: str) -> datetime:
    if bucket == "hour":
        return ts.replace(minute=0, second=0, microsecond=0)
    if bucket == "day":
        return ts.replace(hour=0, minute=0, second=0, microsecond=0)
    raise ValueError("bucket must be 'hour' or 'day'")


def bucket_counts(timestamps: Iterable[datetime], bucket: str = "hour") -> list[dict]:
    counts = Counter(bucket_start(t, bucket) for t in timestamps)
    return [{"bucket": b.isoformat(), "count": counts[b]} for b in sorted(counts)]


def distribution(values: Iterable[str]) -> list[dict]:
    return [{"name": k, "count": v} for k, v in sorted(Counter(values).items(), key=lambda kv: (-kv[1], kv[0]))]


def average_seconds(pairs: Iterable[tuple[datetime | None, datetime | None]]) -> float | None:
    """Mean duration of pairs where both timestamps exist; None when there is nothing to average."""
    durations = [(end - start).total_seconds() for start, end in pairs if start and end and end >= start]
    return round(sum(durations) / len(durations), 1) if durations else None


def fill_gaps(series: list[dict], bucket: str, start: datetime, end: datetime) -> list[dict]:
    """Add zero-count buckets so charts show quiet periods honestly."""
    have = {datetime.fromisoformat(p["bucket"]): p["count"] for p in series}
    step = timedelta(hours=1) if bucket == "hour" else timedelta(days=1)
    cursor, out = bucket_start(start, bucket), []
    while cursor <= end and len(out) < 2000:
        out.append({"bucket": cursor.isoformat(), "count": have.get(cursor, 0)})
        cursor += step
    return out
