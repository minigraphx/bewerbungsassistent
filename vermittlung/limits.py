"""Requests per minute, counted in memory per key (a person, or an address for redeeming codes)."""
import collections
import threading
import time
from typing import Callable

WINDOW_SECONDS = 60.0


class RateLimiter:
    def __init__(self, per_minute: int, clock: Callable[[], float] = time.monotonic) -> None:
        self._per_minute = per_minute
        self._clock = clock
        self._calls: dict[str, collections.deque] = collections.defaultdict(collections.deque)
        self._lock = threading.Lock()

    def _forget_quiet_keys(self, now: float) -> None:
        """Keys can be addresses: keep none longer than the window needs. Call with the lock held."""
        active = {key: calls for key, calls in self._calls.items() if calls and now - calls[-1] < WINDOW_SECONDS}
        self._calls = collections.defaultdict(collections.deque, active)

    def acquire(self, key: str) -> int:
        """0 if the call may go ahead (and counts it), else the seconds to wait."""
        now = self._clock()
        with self._lock:
            self._forget_quiet_keys(now)
            calls = self._calls[key]
            while calls and now - calls[0] >= WINDOW_SECONDS:
                calls.popleft()
            if len(calls) >= self._per_minute:
                return max(1, int(WINDOW_SECONDS - (now - calls[0])) + 1)
            calls.append(now)
            return 0
