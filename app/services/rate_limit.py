from collections import defaultdict, deque
from threading import Lock
import time


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after


class SlidingWindowRateLimiter:
    def __init__(self, ip_limit: int, widget_limit: int, window_seconds: int):
        self.ip_limit = ip_limit
        self.widget_limit = widget_limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, ip: str, widget_id: str) -> None:
        now = time.monotonic()
        with self._lock:
            checks = [(f"ip:{ip}", self.ip_limit), (f"widget:{widget_id}", self.widget_limit)]
            retry_after = 0
            for key, limit in checks:
                events = self._prune(key, now)
                if len(events) >= limit:
                    retry_after = max(retry_after, max(1, int(self.window_seconds - (now - events[0])) + 1))
            if retry_after:
                raise RateLimitExceeded(retry_after)
            for key, _ in checks:
                self._events[key].append(now)

    def _prune(self, key: str, now: float) -> deque[float]:
        events = self._events[key]
        cutoff = now - self.window_seconds
        while events and events[0] <= cutoff:
            events.popleft()
        return events


class NoopRateLimiter:
    def check(self, ip: str, widget_id: str) -> None:
        return None
