"""In-memory sliding-window rate limiter.

Limitation: state is per process. With several workers or instances, limits apply per worker.
A shared store (Redis) is the documented production upgrade path.
"""

import math
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.core.exceptions import RateLimitError
from app.utils.network import get_client_ip


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(
        self, key: str, limit: int, window_seconds: int, now: float | None = None
    ) -> int | None:
        """Record a hit. Return seconds to wait if the limit is exceeded, else None."""
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, math.ceil(hits[0] + window_seconds - now))
            hits.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def rate_limit(scope: str, attempts_field: str, window_field: str) -> Callable[..., None]:
    def dependency(request: Request, settings: Settings = Depends(get_settings)) -> None:
        if not settings.rate_limit_enabled:
            return
        retry_after = limiter.check(
            f"{scope}:{get_client_ip(request)}",
            getattr(settings, attempts_field),
            getattr(settings, window_field),
        )
        if retry_after is not None:
            raise RateLimitError(retry_after)

    return dependency
