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
from adg.control_plane.models.directory import Role, User, UserRole
from adg.control_plane.models.governance import ResourcePolicy
from adg.control_plane.models.resource import Resource
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


@pytest.mark.anyio
async def test_streamable_mcp_server_lists_tools_and_calls_runtime_tool() -> None:
    app, _ = build_streamable_mcp_app()

    async with runtime_mcp_server.session_manager.run():
        for base_url in ["http://127.0.0.1:8000", "http://101.200.0.241:8001"]:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url=base_url,
                headers={"X-ADG-API-Key": "adg_runtime"},
            ) as http_client:
                async with streamable_http_client(
                    f"{base_url}/mcp",
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
