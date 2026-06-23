from __future__ import annotations

import hashlib
import importlib
import threading
import time
from dataclasses import dataclass
from typing import Protocol, cast

from adg.app.settings import Settings, get_settings

RATE_LIMIT_DETAIL = "Too many authentication failures"
_MISSING_KEY_SENTINEL = "<missing>"


class RedisClient(Protocol):
    """Minimal synchronous Redis API used by the auth failure limiter."""

    def incr(self, key: str) -> int: ...

    def expire(self, key: str, seconds: int) -> object: ...

    def setex(self, key: str, seconds: int, value: int) -> object: ...

    def exists(self, key: str) -> int: ...

    def delete(self, *keys: str) -> object: ...


@dataclass
class MemoryFailureBucket:
    failures: int
    window_expires_at: float
    blocked_until: float | None = None


class AuthRateLimiter:
    """Track API-key authentication failures without exposing key existence."""

    def __init__(self, settings: Settings, redis_client: RedisClient | None = None) -> None:
        self._settings = settings
        self._redis_client = redis_client
        self._memory_buckets: dict[str, MemoryFailureBucket] = {}
        self._lock = threading.Lock()

    def check_auth_rate_limited(
        self,
        raw_api_key: str | None,
        client_identifier: str | None = None,
    ) -> bool:
        """Return whether the credential or client failure bucket is blocked."""

        if not self._settings.auth_rate_limit_enabled:
            return False
        fingerprints = self._bucket_fingerprints(raw_api_key, client_identifier)
        if self._settings.auth_rate_limit_storage == "redis":
            return any(self._redis_is_blocked(fingerprint) for fingerprint in fingerprints)
        return any(self._memory_is_blocked(fingerprint) for fingerprint in fingerprints)

    def record_auth_failure(
        self,
        raw_api_key: str | None,
        client_identifier: str | None = None,
    ) -> bool:
        """Record one failure and return whether the caller should now be blocked."""

        if not self._settings.auth_rate_limit_enabled:
            return False
        blocked = False
        for fingerprint in self._bucket_fingerprints(raw_api_key, client_identifier):
            if self._settings.auth_rate_limit_storage == "redis":
                blocked = self._redis_record_failure(fingerprint) or blocked
            else:
                blocked = self._memory_record_failure(fingerprint) or blocked
        return blocked

    def record_auth_success(
        self,
        raw_api_key: str | None,
        client_identifier: str | None = None,
    ) -> None:
        """Clear only the credential bucket after successful authentication."""

        if not self._settings.auth_rate_limit_enabled:
            return
        fingerprint = self._fingerprint("key", raw_api_key)
        if self._settings.auth_rate_limit_storage == "redis":
            client = self._require_redis_client()
            client.delete(self._failure_key(fingerprint), self._block_key(fingerprint))
            return
        with self._lock:
            self._memory_buckets.pop(fingerprint, None)

    def _memory_is_blocked(self, fingerprint: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._memory_buckets.get(fingerprint)
            if bucket is None:
                return False
            if bucket.blocked_until is not None:
                if bucket.blocked_until > now:
                    return True
                self._memory_buckets.pop(fingerprint, None)
                return False
            if bucket.window_expires_at <= now:
                self._memory_buckets.pop(fingerprint, None)
            return False

    def _memory_record_failure(self, fingerprint: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._memory_buckets.get(fingerprint)
            if bucket is None or bucket.window_expires_at <= now:
                bucket = MemoryFailureBucket(
                    failures=0,
                    window_expires_at=now + self._settings.auth_rate_limit_window_seconds,
                )
                self._memory_buckets[fingerprint] = bucket
            bucket.failures += 1
            if bucket.failures >= self._settings.auth_rate_limit_max_failures:
                bucket.blocked_until = now + self._settings.auth_rate_limit_block_seconds
                return True
            return False

    def _redis_is_blocked(self, fingerprint: str) -> bool:
        client = self._require_redis_client()
        return bool(client.exists(self._block_key(fingerprint)))

    def _redis_record_failure(self, fingerprint: str) -> bool:
        client = self._require_redis_client()
        failure_key = self._failure_key(fingerprint)
        failures = int(client.incr(failure_key))
        if failures == 1:
            client.expire(failure_key, self._settings.auth_rate_limit_window_seconds)
        if failures >= self._settings.auth_rate_limit_max_failures:
            client.setex(
                self._block_key(fingerprint),
                self._settings.auth_rate_limit_block_seconds,
                1,
            )
            client.delete(failure_key)
            return True
        return False

    def _require_redis_client(self) -> RedisClient:
        if self._redis_client is None:
            if self._settings.auth_rate_limit_redis_url is None:
                raise RuntimeError("ADG_AUTH_RATE_LIMIT_REDIS_URL is required for redis storage")
            self._redis_client = create_redis_client(self._settings.auth_rate_limit_redis_url)
        return self._redis_client

    def _bucket_fingerprints(
        self,
        raw_api_key: str | None,
        client_identifier: str | None,
    ) -> list[str]:
        fingerprints = [self._fingerprint("key", raw_api_key)]
        if client_identifier not in {None, ""}:
            fingerprints.append(self._fingerprint("client", client_identifier))
        return fingerprints

    def _fingerprint(self, namespace: str, value: str | None) -> str:
        safe_value = value if value not in {None, ""} else _MISSING_KEY_SENTINEL
        return hashlib.sha256(f"{namespace}:{safe_value}".encode()).hexdigest()

    def _failure_key(self, fingerprint: str) -> str:
        return f"adg:auth-rate-limit:failure:{fingerprint}"

    def _block_key(self, fingerprint: str) -> str:
        return f"adg:auth-rate-limit:block:{fingerprint}"


def create_redis_client(redis_url: str) -> RedisClient:
    """Create a Redis client lazily so memory-only deployments need no Redis package."""

    try:
        redis_module = importlib.import_module("redis")
    except ImportError as exc:  # pragma: no cover - depends on optional deployment package
        raise RuntimeError("Install redis to use ADG_AUTH_RATE_LIMIT_STORAGE=redis") from exc
    client = redis_module.Redis.from_url(redis_url, decode_responses=True)
    return cast(RedisClient, client)


_auth_rate_limiter: AuthRateLimiter | None = None
_auth_rate_limiter_lock = threading.Lock()


def get_auth_rate_limiter() -> AuthRateLimiter:
    """Return the shared limiter configured from current settings."""

    global _auth_rate_limiter
    with _auth_rate_limiter_lock:
        if _auth_rate_limiter is None:
            settings = get_settings()
            redis_client = None
            if settings.auth_rate_limit_storage == "redis" and settings.auth_rate_limit_redis_url:
                redis_client = create_redis_client(settings.auth_rate_limit_redis_url)
            _auth_rate_limiter = AuthRateLimiter(settings, redis_client)
        return _auth_rate_limiter


def reset_auth_rate_limiter() -> None:
    """Reset cached limiter state for tests and settings reloads."""

    global _auth_rate_limiter
    with _auth_rate_limiter_lock:
        _auth_rate_limiter = None


def check_auth_rate_limited(
    raw_api_key: str | None,
    client_identifier: str | None = None,
) -> bool:
    return get_auth_rate_limiter().check_auth_rate_limited(raw_api_key, client_identifier)


def record_auth_failure(
    raw_api_key: str | None,
    client_identifier: str | None = None,
) -> bool:
    return get_auth_rate_limiter().record_auth_failure(raw_api_key, client_identifier)


def record_auth_success(
    raw_api_key: str | None,
    client_identifier: str | None = None,
) -> None:
    get_auth_rate_limiter().record_auth_success(raw_api_key, client_identifier)
