"""
discovery/rate_limiter.py

Shared rate limiter for Groq calls. Your org's TPM (tokens-per-minute)
limit is account-wide, not per-file — filter.py and
extract_from_listings.py both draw from the SAME 6000 TPM budget, so
they need to share one limiter, not each throttle independently.

This is a sliding-window limiter: it tracks call timestamps from the
last `period_seconds` and blocks new calls once `max_calls` is hit
within that window, rather than a fixed delay between calls. Thread-safe
via a lock, so it's safe to call .acquire() from multiple worker threads
in a ThreadPoolExecutor.

Tune MAX_CALLS_PER_MINUTE based on your actual prompt size. Rough math:
6000 TPM / ~400 tokens per call ≈ 15 calls/minute. Kept conservative at
12 to leave headroom for prompts that run a bit longer.
"""

import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self, max_calls: int, period_seconds: float = 60.0):
        self.max_calls = max_calls
        self.period = period_seconds
        self.calls = deque()
        self.lock = threading.Lock()

    def acquire(self):
        """Blocks until it's safe to make another call, then reserves a slot."""
        while True:
            with self.lock:
                now = time.monotonic()
                while self.calls and now - self.calls[0] > self.period:
                    self.calls.popleft()

                if len(self.calls) < self.max_calls:
                    self.calls.append(now)
                    return

                wait = self.period - (now - self.calls[0])

            time.sleep(max(wait, 0.05))


# Shared across filter.py and extract_from_listings.py — both import
# THIS SAME instance so they respect one combined budget, not two
# separate ones that together still blow past 6000 TPM.
groq_rate_limiter = RateLimiter(max_calls=12, period_seconds=60.0)
