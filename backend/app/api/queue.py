"""
Phase 4: Rate-Limited Request Queue
=====================================
Per-IP rate limiter + global Groq request queue to protect the shared
free-tier quota from being exhausted by a single user or burst.
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class PerIPRateLimiter:
    """Token bucket per client IP — stops one user monopolizing the shared Groq quota."""

    def __init__(self, rpm: int = 5):
        self.rpm = rpm
        self._buckets: dict[str, dict] = {}

    def allow(self, ip: str) -> bool:
        now = time.monotonic()
        bucket = self._buckets.get(ip)
        if bucket is None:
            self._buckets[ip] = {"tokens": self.rpm - 1, "last_refill": now}
            return True

        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(self.rpm, bucket["tokens"] + elapsed * (self.rpm / 60.0))
        bucket["last_refill"] = now

        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False

    def retry_after(self, ip: str) -> float:
        bucket = self._buckets.get(ip)
        if bucket is None:
            return 0.0
        return max(0.0, (1 - bucket["tokens"]) * (60.0 / self.rpm))


class GlobalGroqQueue:
    """Ensures total outbound LLM calls stay under Groq's RPM budget."""

    def __init__(self, max_concurrent: int = 5, rpm_budget: int = 25):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.rpm_budget = rpm_budget
        self._call_timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def _wait_for_rpm_slot(self):
        while True:
            now = time.monotonic()
            async with self._lock:
                self._call_timestamps = [t for t in self._call_timestamps if now - t < 60]
                if len(self._call_timestamps) < self.rpm_budget:
                    self._call_timestamps.append(now)
                    return
            await asyncio.sleep(1)

    async def submit(self, coro):
        async with self._semaphore:
            await self._wait_for_rpm_slot()
            return await coro
