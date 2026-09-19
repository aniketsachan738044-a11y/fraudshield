import logging
import time
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException, Request, status

from app.config import get_settings

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    settings = get_settings()
    if settings.trust_proxy_headers:
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()

        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip:
            return x_real_ip.strip()

        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

    return request.client.host if request.client else "unknown"


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._last_cleanup = monotonic()
        self._redis = None
        self._init_redis()

    def _init_redis(self) -> None:
        settings = get_settings()
        if settings.redis_url:
            try:
                import redis

                client = redis.from_url(settings.redis_url, socket_timeout=1.0, decode_responses=True)
                client.ping()
                self._redis = client
                logger.info("Distributed Redis rate limiter connected successfully")
            except Exception as exc:
                logger.warning(f"Redis connection failed, falling back to in-memory limiter: {exc}")
                self._redis = None

    def _cleanup_stale_keys(self, now: float) -> None:
        if now - self._last_cleanup < self.window_seconds:
            return
        keys_to_remove = [
            key for key, hits in self._hits.items()
            if not hits or (now - hits[-1] > self.window_seconds)
        ]
        for key in keys_to_remove:
            self._hits.pop(key, None)
        self._last_cleanup = now

    def check(self, key: str) -> None:
        # 1. Try Redis distributed rate limiting if available
        if self._redis:
            try:
                now_ts = time.time()
                redis_key = f"ratelimit:{key}"
                pipe = self._redis.pipeline()
                pipe.zremrangebyscore(redis_key, 0, now_ts - self.window_seconds)
                pipe.zcard(redis_key)
                pipe.zadd(redis_key, {str(uuid4()): now_ts})
                pipe.expire(redis_key, self.window_seconds + 10)
                results = pipe.execute()
                current_hits = results[1]
                if current_hits >= self.limit:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many attempts. Please wait a few minutes and try again.",
                    )
                return
            except HTTPException:
                raise
            except Exception as exc:
                logger.warning(f"Redis rate limit check failed, using in-memory fallback: {exc}")

        # 2. In-memory sliding-window fallback
        now = monotonic()
        with self._lock:
            self._cleanup_stale_keys(now)
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
    client_ip = get_client_ip(request)
    login_limiter.check(f"login:{client_ip}")
