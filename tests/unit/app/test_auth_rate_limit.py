from typing import cast

from pytest import MonkeyPatch

from adg.app.auth_rate_limit import AuthRateLimiter, RedisClient
from adg.app.settings import Settings


def memory_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "auth_rate_limit_storage": "memory",
        "auth_rate_limit_window_seconds": 60,
        "auth_rate_limit_max_failures": 100,
        "auth_rate_limit_block_seconds": 300,
        "auth_rate_limit_memory_max_buckets": 4,
    }
    values.update(overrides)
    return Settings.model_validate(values)


def test_memory_limiter_keeps_block_until_block_ttl_expires(monkeypatch: MonkeyPatch) -> None:
    now = [0.0]
    monkeypatch.setattr("adg.app.auth_rate_limit.time.monotonic", lambda: now[0])
    limiter = AuthRateLimiter(
        memory_settings(
            auth_rate_limit_window_seconds=1,
            auth_rate_limit_max_failures=2,
            auth_rate_limit_block_seconds=10,
        )
    )

    assert limiter.record_auth_failure("wrong") is False
    assert limiter.record_auth_failure("wrong") is True
    now[0] = 2.0

    assert limiter.record_auth_failure("wrong") is True


def test_memory_limiter_bounds_buckets_and_preserves_hot_client_bucket() -> None:
    limiter = AuthRateLimiter(memory_settings())

    for index in range(10):
        limiter.record_auth_failure(f"wrong-{index}", "shared-proxy")

    client_fingerprint = limiter._fingerprint("client", "shared-proxy")
    assert len(limiter._memory_buckets) <= 4
    assert client_fingerprint in limiter._memory_buckets


class AtomicRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}
        self.eval_calls: list[tuple[str, int, tuple[object, ...]]] = []

    def eval(self, script: str, numkeys: int, *keys_and_args: object) -> int:
        self.eval_calls.append((script, numkeys, keys_and_args))
        failure_key = str(keys_and_args[0])
        block_key = str(keys_and_args[1])
        window_seconds = int(str(keys_and_args[2]))
        max_failures = int(str(keys_and_args[3]))
        block_seconds = int(str(keys_and_args[4]))
        if block_key in self.values:
            return 1
        failures = self.values.get(failure_key, 0) + 1
        self.values[failure_key] = failures
        if failures == 1:
            self.expirations[failure_key] = window_seconds
        if failures >= max_failures:
            self.values[block_key] = 1
            self.expirations[block_key] = block_seconds
            self.delete(failure_key)
            return 1
        return 0

    def exists(self, key: str) -> int:
        return int(key in self.values)

    def delete(self, *keys: str) -> None:
        for key in keys:
            self.values.pop(key, None)
            self.expirations.pop(key, None)


def test_redis_failure_update_is_atomic_and_cluster_slot_safe() -> None:
    redis_client = AtomicRedisClient()
    limiter = AuthRateLimiter(
        Settings(
            auth_rate_limit_storage="redis",
            auth_rate_limit_redis_url="redis://localhost:6379/0",
            auth_rate_limit_window_seconds=60,
            auth_rate_limit_max_failures=2,
            auth_rate_limit_block_seconds=300,
        ),
        cast(RedisClient, redis_client),
    )

    assert limiter.record_auth_failure("wrong") is False
    assert limiter.record_auth_failure("wrong") is True

    script, numkeys, keys_and_args = redis_client.eval_calls[0]
    failure_key = str(keys_and_args[0])
    block_key = str(keys_and_args[1])
    assert numkeys == 2
    assert "INCR" in script
    assert "EXPIRE" in script
    assert "SETEX" in script
    assert failure_key.rsplit(":", 1)[0] == block_key.rsplit(":", 1)[0]
    assert "{" in failure_key and "}" in failure_key
