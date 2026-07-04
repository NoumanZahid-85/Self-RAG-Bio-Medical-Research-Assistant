import time
from unittest.mock import patch

import pytest
from backend.app.api.queue import GlobalGroqQueue, PerIPRateLimiter


class TestPerIPRateLimiter:
    def test_allow_first_request(self):
        limiter = PerIPRateLimiter(rpm=5)
        assert limiter.allow("127.0.0.1") is True

    def test_blocks_when_exhausted(self):
        limiter = PerIPRateLimiter(rpm=2)
        assert limiter.allow("10.0.0.1") is True
        assert limiter.allow("10.0.0.1") is True
        assert limiter.allow("10.0.0.1") is False

    def test_different_ips_independent(self):
        limiter = PerIPRateLimiter(rpm=1)
        assert limiter.allow("192.168.1.1") is True
        assert limiter.allow("192.168.1.1") is False
        assert limiter.allow("10.0.0.2") is True

    def test_retry_after_when_not_limited(self):
        limiter = PerIPRateLimiter(rpm=5)
        limiter.allow("1.2.3.4")
        assert limiter.retry_after("1.2.3.4") == 0.0

    def test_retry_after_when_limited(self):
        limiter = PerIPRateLimiter(rpm=2)
        limiter.allow("5.6.7.8")
        limiter.allow("5.6.7.8")
        limiter.allow("5.6.7.8")
        assert limiter.retry_after("5.6.7.8") > 0.0

    def test_unknown_ip_retry_after_zero(self):
        limiter = PerIPRateLimiter(rpm=5)
        assert limiter.retry_after("unknown") == 0.0

    def test_token_refill_over_time(self):
        limiter = PerIPRateLimiter(rpm=60)
        limiter.allow("refill-test")
        now = time.monotonic()
        with patch(f"{PerIPRateLimiter.__module__}.time.monotonic", return_value=now + 30):
            assert limiter.allow("refill-test") is True

    def test_rate_limiter_init_default_rpm(self):
        limiter = PerIPRateLimiter()
        assert limiter.rpm == 5


class TestGlobalGroqQueue:
    @pytest.mark.asyncio
    async def test_submit_runs_coro(self):
        queue = GlobalGroqQueue(max_concurrent=5, rpm_budget=100)
        result = await queue.submit(async_fn(42))
        assert result == 42

    @pytest.mark.asyncio
    async def test_submit_respects_concurrency_limit(self):
        queue = GlobalGroqQueue(max_concurrent=1, rpm_budget=100)

        async def slow():
            return "done"

        r1 = await queue.submit(slow())
        assert r1 == "done"


async def async_fn(value):
    return value
