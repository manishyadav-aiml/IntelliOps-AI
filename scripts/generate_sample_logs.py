"""Generate SYNTHETIC sample logs (deterministic). Not real production data.

Usage: python scripts/generate_sample_logs.py
Writes to data/sample_logs/. Standard library only.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "sample_logs"
START = datetime(2026, 3, 1, 9, 0, 0)
HOSTS = ["app-01", "app-02", "db-01", "pay-01"]


def fmt(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d %H:%M:%S") + f",{ts.microsecond // 1000:03d}"


def normal_traffic(rng: random.Random, ts: datetime, n: int) -> tuple[list[str], datetime]:
    lines = []
    for _ in range(n):
        ts += timedelta(seconds=rng.uniform(0.5, 3))
        r = rng.random()
        if r < 0.55:
            lines.append(f"{fmt(ts)} INFO [api-gateway] GET /api/orders/{rng.randint(1000, 9999)} 200 in {rng.randint(15, 90)} ms host={rng.choice(HOSTS[:2])}")
        elif r < 0.8:
            lines.append(f"{fmt(ts)} INFO [auth-service] User {rng.randint(100, 999)} logged in from 10.0.{rng.randint(0, 5)}.{rng.randint(2, 250)}")
        elif r < 0.95:
            lines.append(f"{fmt(ts)} INFO [payment-service] Payment {rng.randint(90000, 99999)} authorised amount={rng.randint(5, 500)} host=pay-01")
        else:
            lines.append(f"{fmt(ts)} WARN [db] Slow query took {rng.randint(300, 900)} ms host=db-01")
    return lines, ts


def write_normal(rng: random.Random) -> None:
    lines, _ = normal_traffic(rng, START, 1200)
    (OUT / "normal_activity.log").write_text("\n".join(lines) + "\n")


def write_payment_incident(rng: random.Random) -> None:
    ts = START + timedelta(hours=2)
    lines, ts = normal_traffic(rng, ts, 420)  # ~10 min of normal traffic before the incident
    for i in range(25):  # database timeouts, then payment failures, then service unavailable
        ts += timedelta(seconds=rng.uniform(0.2, 1.2))
        lines.append(f"{fmt(ts)} ERROR [db] Connection timeout after 30000 ms to 10.0.1.15:5432 host=db-01")
        if i % 2 == 0:
            lines.append(f"{fmt(ts)} ERROR [payment-service] Payment {rng.randint(90000, 99999)} failed: database unavailable host=pay-01")
        if i % 5 == 0:
            lines.append(f"{fmt(ts)} WARN [api-gateway] Upstream latency {rng.randint(2000, 9000)} ms for /api/pay host=app-01")
    for _ in range(8):
        ts += timedelta(seconds=rng.uniform(0.2, 1))
        lines.append(f"{fmt(ts)} CRITICAL [payment-service] Service unavailable: circuit breaker open host=pay-01")
        lines.append(f"{fmt(ts)} ERROR [network] Connection refused to 10.0.2.20:8443 host=app-02")
    ts += timedelta(minutes=2)
    more, ts = normal_traffic(rng, ts, 150)
    lines.append(f"{fmt(ts)} WARN [system] Memory usage at {rng.randint(88, 96)} percent host=app-02")
    lines += more
    (OUT / "incident_payment_failure.log").write_text("\n".join(lines) + "\n")


def write_auth_csv(rng: random.Random) -> None:
    ts = START + timedelta(hours=4)
    with open(OUT / "auth_failures.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "level", "service", "host", "message"])
        for i in range(120):
            ts += timedelta(seconds=rng.uniform(0.5, 4))
            if 40 <= i < 90:  # brute-force style burst
                writer.writerow([fmt(ts), "ERROR", "auth-service", "app-01", f"Authentication failed for user admin from 203.0.113.{rng.randint(2, 30)}"])
            else:
                writer.writerow([fmt(ts), "INFO", "auth-service", "app-01", f"User {rng.randint(100, 999)} logged in"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    write_normal(rng)
    write_payment_incident(rng)
    write_auth_csv(rng)
    print("Wrote:", ", ".join(sorted(p.name for p in OUT.iterdir())))


if __name__ == "__main__":
    main()
