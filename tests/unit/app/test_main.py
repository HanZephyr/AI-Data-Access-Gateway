from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from adg.app.main import create_app


def test_app_lifespan_disposes_runtime_engine_cache_on_shutdown(
    monkeypatch: MonkeyPatch,
) -> None:
    disposed: list[bool] = []

    @asynccontextmanager
    async def run_session_manager_once() -> AsyncGenerator[None]:
        yield

    monkeypatch.setattr(
        "adg.app.main.runtime_engine_cache.dispose_all",
        lambda: disposed.append(True),
    )

    app = create_app()
    monkeypatch.setattr(
        "adg.app.main.runtime_mcp_server.session_manager.run",
        run_session_manager_once,
    )
    with TestClient(app):
        assert disposed == []

    assert disposed == [True]
