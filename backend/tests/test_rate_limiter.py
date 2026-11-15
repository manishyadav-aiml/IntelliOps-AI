from app.core.rate_limit import SlidingWindowLimiter


def test_blocks_after_limit_then_recovers() -> None:
    limiter = SlidingWindowLimiter()
    for i in range(3):
        assert limiter.check("k", 3, 60, now=100.0 + i) is None
    retry = limiter.check("k", 3, 60, now=103.0)
    assert retry is not None and retry >= 1
    assert limiter.check("k", 3, 60, now=161.0) is None  # oldest hit has expired


def test_keys_are_independent() -> None:
    limiter = SlidingWindowLimiter()
    assert limiter.check("a", 1, 60, now=0.0) is None
    assert limiter.check("a", 1, 60, now=1.0) is not None
    assert limiter.check("b", 1, 60, now=1.0) is None
