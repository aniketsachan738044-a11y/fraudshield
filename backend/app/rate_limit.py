from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()

        if len(hits) >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please wait a few minutes and try again.",
            )

        hits.append(now)


login_limiter = SlidingWindowRateLimiter(limit=8, window_seconds=300)


def limit_login_attempts(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    login_limiter.check(f"login:{client_host}")

