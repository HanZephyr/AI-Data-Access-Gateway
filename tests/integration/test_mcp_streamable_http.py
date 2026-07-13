import inspect
from collections.abc import Callable
from typing import Any, cast

import httpx
import pytest
from fastapi import FastAPI
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy.orm import Session, sessionmaker

from adg.app.main import create_app
from adg.app.settings import get_settings
from adg.control_plane.db import create_engine_from_url, create_session_factory
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.directory import Role, User, UserRole
from adg.control_plane.models.governance import ResourcePolicy
from adg.control_plane.models.resource import Resource
from adg.mcp_server import server as mcp_server_module
from adg.mcp_server.server import runtime_mcp_server
from adg.shared.security import hash_api_key


def build_streamable_mcp_app() -> tuple[FastAPI, sessionmaker[Session]]:
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            User(
                id="user_1",
                name="Alice",
                external_ref="u001",
                org_node_id=None,
                status="active",
            )
        )
        session.add(Role(id="role_finance", name="Finance"))
        session.add(UserRole(user_id="user_1", role_id="role_finance"))
        session.add(
            ApiKey(
                id="key_runtime",
                name="runtime",
                key_hash=hash_api_key("adg_runtime"),
                user_id="user_1",
                status="active",
                scopes='["runtime"]',
            )
        )
        session.add(
            Datasource(
                id="ds_1",
                name="Warehouse",
                type="postgres",
                datasource_kind="relational",
                config_json="{}",
                status="active",
            )
        )
        session.add(
            Resource(
                id="res_customers",
                datasource_id="ds_1",
                parent_id=None,
                kind="relational_table",
                name="customers",
                path="warehouse.public.customers",
                display_name="customers",
                query_language="sql",
                status="active",
                metadata_json="{}",
            )
        )
        session.add(
            ResourcePolicy(
                subject_type="user",
                subject_id="user_1",
                effect="allow",
                action="read",
                resource_id="res_customers",
                status="active",
            )
        )
        session.commit()

    return create_app(session_factory=session_factory), session_factory


@pytest.fixture(autouse=True)
def reset_streamable_mcp_session_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create a new one-shot FastMCP session manager for every integration test."""

    monkeypatch.setattr(runtime_mcp_server, "_session_manager", None)


async def assert_mcp_list_datasources(
    app: FastAPI,
    *,
    headers: dict[str, str],
    query: str = "",
) -> None:
    async with runtime_mcp_server.session_manager.run():
        base_url = "http://127.0.0.1:8000"
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=base_url,
            headers=headers,
        ) as http_client:
            async with streamable_http_client(
                f"{base_url}/mcp{query}",
                http_client=http_client,
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    tools = await session.list_tools()
                    list_datasources_tool = next(
                        tool for tool in tools.tools if tool.name == "list_datasources"
                    )
                    properties = list_datasources_tool.inputSchema.get("properties", {})
                    assert "user_id" not in properties
                    assert "roles" not in properties
                    assert "groups" not in properties

                    result = await session.call_tool("list_datasources", {})
                    assert result.structuredContent is not None
                    assert result.structuredContent["datasources"][0]["id"] == "ds_1"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("headers", "query"),
    [
        ({"X-ADG-API-Key": "adg_runtime"}, ""),
        ({}, "?apikey=adg_runtime"),
        ({"Authorization": "bEaReR adg_runtime"}, ""),
    ],
)
async def test_streamable_mcp_server_accepts_runtime_api_key_sources(
    headers: dict[str, str],
    query: str,
) -> None:
    app, _ = build_streamable_mcp_app()

    await assert_mcp_list_datasources(app, headers=headers, query=query)


@pytest.mark.anyio
async def test_streamable_mcp_server_accepts_configured_api_key_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADG_API_KEY_HEADER", "X-Custom-ADG-Key")
    get_settings.cache_clear()
    try:
        app, _ = build_streamable_mcp_app()

        await assert_mcp_list_datasources(
            app,
            headers={"X-Custom-ADG-Key": "adg_runtime"},
        )
    finally:
        monkeypatch.delenv("ADG_API_KEY_HEADER", raising=False)
        get_settings.cache_clear()


@pytest.mark.anyio
async def test_streamable_mcp_server_accepts_matching_api_key_credentials() -> None:
    app, _ = build_streamable_mcp_app()

    await assert_mcp_list_datasources(
        app,
        headers={
            "X-ADG-API-Key": "adg_runtime",
            "Authorization": "Bearer adg_runtime",
        },
        query="?apikey=adg_runtime",
    )


@pytest.mark.anyio
async def test_streamable_mcp_server_rejects_conflicting_api_key_credentials() -> None:
    app, _ = build_streamable_mcp_app()

    async with runtime_mcp_server.session_manager.run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1:8000",
        ) as http_client:
            response = await http_client.post(
                "/mcp?apikey=adg_other",
                content="{}",
                headers={
                    "Content-Type": "application/json",
                    "X-ADG-API-Key": "adg_runtime",
                },
            )

    assert response.status_code == 400
    assert response.json() == {"detail": "Conflicting API key credentials"}


@pytest.mark.anyio
async def test_streamable_mcp_server_rejects_missing_api_key() -> None:
    app, _ = build_streamable_mcp_app()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8000",
    ) as http_client:
        response = await http_client.post("/mcp")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing API key"}


@pytest.mark.anyio
async def test_mcp_tool_handlers_are_async_and_run_runtime_work_in_threadpool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, tuple[Any, ...]]] = []

    def fake_run_runtime_tool(
        ctx: object,
        tool_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {"tool_name": tool_name, "payload": payload, "ctx": ctx is fake_ctx}

    async def fake_run_sync(
        function: Callable[..., object],
        *args: object,
    ) -> dict[str, Any]:
        calls.append((function.__name__, args))
        return cast(dict[str, Any], function(*args))

    fake_ctx = object()
    monkeypatch.setattr(mcp_server_module, "_run_runtime_tool", fake_run_runtime_tool)
    monkeypatch.setattr(mcp_server_module, "_run_in_threadpool", fake_run_sync)

    assert inspect.iscoroutinefunction(mcp_server_module.list_datasources)

    result = await mcp_server_module.list_datasources(fake_ctx)

    assert result == {"tool_name": "list_datasources", "payload": {}, "ctx": True}
    assert calls == [("fake_run_runtime_tool", (fake_ctx, "list_datasources", {}))]
