"""Rate limiter de janela deslizante em memória (por IP e bucket)."""
import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, window_seconds: int = 60):
        self.window = window_seconds
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            if len(self._hits) > 10_000:  # evita crescimento ilimitado de chaves
                for k in [k for k, v in self._hits.items() if not v]:
                    del self._hits[k]
            return True


rate_limiter = RateLimiter()
