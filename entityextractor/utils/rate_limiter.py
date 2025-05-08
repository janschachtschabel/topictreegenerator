import time
import threading
import logging
import random
from functools import wraps

class RateLimiter:
    """
    A simple thread-safe rate limiter with exponential backoff on HTTP 429 errors.
    """
    def __init__(self, max_calls, period, backoff_base=1, backoff_max=60):
        self.max_calls = max_calls
        self.period = period
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.lock = threading.Lock()
        self.calls = []

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                now = time.time()
                # retain only calls within period
                self.calls = [t for t in self.calls if t > now - self.period]
                if len(self.calls) >= self.max_calls:
                    sleep_t = self.calls[0] + self.period - now
                    logging.info(f"[RateLimiter] Rate limit reached, sleeping {sleep_t:.2f}s")
                    time.sleep(sleep_t)
                self.calls.append(time.time())
            try:
                return func(*args, **kwargs)
            except Exception as e:
                resp = getattr(e, 'response', None)
                if resp is not None and getattr(resp, 'status_code', None) == 429:
                    # exponential backoff with jitter
                    expo = min(self.backoff_base * 2 ** len(self.calls), self.backoff_max)
                    jitter = expo * random.uniform(-0.1, 0.1)
                    sleep_t = expo + jitter
                    logging.warning(f"[RateLimiter] 429 received, backing off for {sleep_t:.2f}s")
                    time.sleep(sleep_t)
                    return wrapper(*args, **kwargs)
                raise
        return wrapper
