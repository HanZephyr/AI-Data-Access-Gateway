import httpx
import pytest
from fastapi import FastAPI
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy.orm import Session, sessionmaker

from adg.app.main import create_app
from adg.control_plane.db import create_engine_from_url, create_session_factory
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.datasource import Datasource
from adg.mcp_server.server import runtime_mcp_server
from adg.shared.security import hash_api_key


def build_streamable_mcp_app() -> tuple[FastAPI, sessionmaker[Session]]:
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            ApiKey(
                id="key_runtime",
                name="runtime",
                key_hash=hash_api_key("adg_runtime"),
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
        session.commit()

    return create_app(session_factory=session_factory), session_factory


@pytest.mark.anyio
async def test_streamable_mcp_server_lists_tools_and_calls_runtime_tool() -> None:
    app, _ = build_streamable_mcp_app()

    async with runtime_mcp_server.session_manager.run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1:8000",
            headers={"X-ADG-API-Key": "adg_runtime"},
        ) as http_client:
            async with streamable_http_client(
                "http://127.0.0.1:8000/mcp",
                http_client=http_client,
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    tools = await session.list_tools()
                    assert any(tool.name == "list_datasources" for tool in tools.tools)

                    result = await session.call_tool("list_datasources", {"user_id": "user-1"})
                    assert result.structuredContent is not None
                    assert result.structuredContent["datasources"][0]["id"] == "ds_1"
