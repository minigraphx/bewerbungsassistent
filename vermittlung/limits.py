"""Limits counted in memory per key: requests per minute (a person, or an address for redeeming codes)
and requests running at once (a person)."""
import collections
import contextlib
import threading
import time
from typing import Callable, Iterator

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


class ParallelLimiter:
    """The budget is checked before a call and charged after it, so calls running at once could all overspend."""

    def __init__(self, at_once: int) -> None:
        self._at_once = at_once
        self._running: collections.Counter = collections.Counter()
        self._lock = threading.Lock()

    @contextlib.contextmanager
    def slot(self, key: str) -> Iterator[bool]:
        """True if the call may run; False means the limit is reached and nothing is held."""
        with self._lock:
            free = self._running[key] < self._at_once
            if free:
                self._running[key] += 1
        try:
            yield free
        finally:
            if free:
                with self._lock:
                    self._running[key] -= 1
                    if not self._running[key]:
                        del self._running[key]
