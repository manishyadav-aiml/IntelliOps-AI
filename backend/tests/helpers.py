"""Shared synthetic data builders for tests (all data is synthetic)."""

import random
from datetime import UTC, datetime, timedelta

from app.ml.preprocessing import LogRow

T0 = datetime(2026, 3, 1, 9, 0, 0, tzinfo=UTC)


def traffic_rows(minutes: int = 60, burst_minute: int | None = 40, seed: int = 1) -> list[LogRow]:
    """Stable INFO/WARNING traffic with an optional error burst on payment-service."""
    rng = random.Random(seed)
    rows: list[LogRow] = []
    for minute in range(minutes):
        base = T0 + timedelta(minutes=minute)
        for i in range(rng.randint(18, 24)):
            service = rng.choice(["api-gateway", "auth-service", "payment-service"])
            rows.append(LogRow(base + timedelta(seconds=i * 2.5), "INFO", service, f"info_{service}"))
        if rng.random() < 0.2:
            rows.append(LogRow(base + timedelta(seconds=50), "WARNING", "db", "slow_query"))
        if minute % 15 == 7:
            rows.append(LogRow(base + timedelta(seconds=30), "ERROR", "db", "db_blip"))
        if burst_minute is not None and minute in (burst_minute, burst_minute + 1):
            for i in range(30):
                rows.append(LogRow(base + timedelta(seconds=i * 1.5), "ERROR", "payment-service", "pay_fail"))
            for i in range(4):
                rows.append(LogRow(base + timedelta(seconds=45 + i), "CRITICAL", "payment-service", "pay_down"))
    return rows
