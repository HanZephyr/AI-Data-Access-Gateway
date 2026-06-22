from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from threading import RLock
from typing import Protocol

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine

from adg.app.settings import get_settings


class RuntimePoolSettings(Protocol):
    runtime_datasource_pool_cache_size: int
    runtime_datasource_pool_idle_ttl_seconds: int
    runtime_datasource_pool_size: int
    runtime_datasource_pool_max_overflow: int


EngineFactory = Callable[..., Engine]
SettingsProvider = Callable[[], RuntimePoolSettings]
Clock = Callable[[], float]


@dataclass
class CacheEntry:
    engine: Engine
    last_used_at: float


ConnectArgs = Mapping[str, object]


def build_cache_key(
    connector_type: str,
    url: URL,
    *,
    connect_args: ConnectArgs | None = None,
) -> str:
    """Build a stable cache key without exposing datasource credentials."""

    payload = {
        "url": url.render_as_string(hide_password=False),
        "connect_args": {
            str(key): repr(value)
            for key, value in sorted((connect_args or {}).items(), key=lambda item: str(item[0]))
        },
    }
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"{connector_type}:{fingerprint}"


class RuntimeEngineCache:
    """Thread-safe LRU cache for runtime datasource SQLAlchemy engines."""

    def __init__(
        self,
        *,
        settings_provider: SettingsProvider | None = None,
        engine_factory: EngineFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._settings_provider = settings_provider or get_settings
        self._engine_factory = engine_factory
        self._clock = clock or time.monotonic
        self._lock = RLock()
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def get_engine(
        self,
        connector_type: str,
        url: URL,
        *,
        connect_args: ConnectArgs | None = None,
    ) -> Engine:
        settings = self._settings_provider()
        now = self._clock()
        key = build_cache_key(connector_type, url, connect_args=connect_args)

        with self._lock:
            self._dispose_expired_locked(now, settings.runtime_datasource_pool_idle_ttl_seconds)

            entry = self._entries.get(key)
            if entry is not None:
                entry.last_used_at = now
                self._entries.move_to_end(key)
                return entry.engine

            engine = self._create_engine(url, settings, connect_args=connect_args)
            self._entries[key] = CacheEntry(engine=engine, last_used_at=now)
            self._entries.move_to_end(key)
            self._enforce_cache_size_locked(settings.runtime_datasource_pool_cache_size)
            return engine

    def dispose_all(self) -> None:
        with self._lock:
            entries = list(self._entries.values())
            self._entries.clear()

        for entry in entries:
            entry.engine.dispose()

    def _create_engine(
        self,
        url: URL,
        settings: RuntimePoolSettings,
        *,
        connect_args: ConnectArgs | None,
    ) -> Engine:
        factory = self._engine_factory or create_engine
        return factory(
            url,
            pool_pre_ping=True,
            pool_size=settings.runtime_datasource_pool_size,
            max_overflow=settings.runtime_datasource_pool_max_overflow,
            connect_args=dict(connect_args or {}),
        )

    def _dispose_expired_locked(self, now: float, idle_ttl_seconds: int) -> None:
        expired_keys = [
            key
            for key, entry in self._entries.items()
            if now - entry.last_used_at > idle_ttl_seconds
        ]
        for key in expired_keys:
            entry = self._entries.pop(key)
            entry.engine.dispose()

    def _enforce_cache_size_locked(self, cache_size: int) -> None:
        while len(self._entries) > cache_size:
            _, entry = self._entries.popitem(last=False)
            entry.engine.dispose()


_runtime_engine_cache = RuntimeEngineCache()


def get_engine(
    connector_type: str,
    url: URL,
    *,
    connect_args: ConnectArgs | None = None,
) -> Engine:
    return _runtime_engine_cache.get_engine(connector_type, url, connect_args=connect_args)


def dispose_all() -> None:
    _runtime_engine_cache.dispose_all()
