from typing import Any, cast

from fastapi import HTTPException
from mcp.server.fastmcp import Context, FastMCP
from sqlalchemy.orm import Session, sessionmaker
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from adg.app.dependencies import AuthenticatedRuntimeKey, authenticate_runtime_api_key_value
from adg.app.settings import get_settings
from adg.control_plane.db import SessionLocal
from adg.gateway_runtime.tools import GatewayRuntimeService
from adg.mcp_api.runtime_tools import RUNTIME_TOOL_DEFINITIONS, dispatch_runtime_tool_call

runtime_mcp_server = FastMCP("AI Data Access Gateway", host="0.0.0.0")
McpContext = Context[Any, Any, Any]


class RuntimeApiKeyMiddleware:
    """Require one runtime-scoped API key on every Streamable HTTP request."""

    def __init__(self, app: ASGIApp, session_factory: sessionmaker[Session]):
        self.app = app
        self._session_factory = session_factory

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(raw=scope["headers"])
        with self._session_factory() as session:
            try:
                authenticated = authenticate_runtime_api_key_value(
                    session,
                    headers.get(get_settings().api_key_header),
                )
            except HTTPException as exc:
                await JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})(
                    scope,
                    receive,
                    send,
                )
                return

        scope.setdefault("state", {})
        cast(dict[str, Any], scope["state"])["authenticated_api_key"] = authenticated
        await self.app(scope, receive, send)


class MountedMcpServerApp:
    """Rewrite the mounted root path to FastMCP's internal /mcp endpoint."""

    def __init__(self, app: Starlette):
        self.app = app
        self.state = app.state

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in {"", "/", "/mcp/"}:
            rewritten_scope = dict(scope)
            rewritten_scope["path"] = "/mcp"
            rewritten_scope["raw_path"] = b"/mcp"
            rewritten_scope["root_path"] = ""
            await self.app(rewritten_scope, receive, send)
            return

        await self.app(scope, receive, send)


def build_mcp_server_app(
    session_factory: sessionmaker[Session] | None = None,
) -> MountedMcpServerApp:
    """Build the mounted Streamable HTTP MCP server app."""

    factory = session_factory or SessionLocal
    inner_app = runtime_mcp_server.streamable_http_app()
    inner_app.state.session_factory = factory
    inner_app.add_middleware(RuntimeApiKeyMiddleware, session_factory=factory)
    return MountedMcpServerApp(inner_app)


def _request_from_context(ctx: McpContext) -> Request:
    """Return the active Starlette request from one MCP tool invocation."""

    request = ctx.request_context.request
    if request is None:  # pragma: no cover
        raise RuntimeError("MCP request context is unavailable")
    return cast(Request, request)


def _run_runtime_tool(ctx: McpContext, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Execute one runtime tool call with authenticated context and commit the audit event."""

    request = _request_from_context(ctx)
    session_factory = cast(
        sessionmaker[Session],
        getattr(request.app.state, "session_factory", SessionLocal),
    )
    authenticated = cast(AuthenticatedRuntimeKey, request.state.authenticated_api_key)

    with session_factory() as session:
        runtime = GatewayRuntimeService(session)
        response = dispatch_runtime_tool_call(
            runtime,
            tool_name,
            payload,
            authenticated.runtime_identity,
            authenticated.id,
        )
        session.commit()
        return response


@runtime_mcp_server.tool(
    name="list_datasources",
    description=RUNTIME_TOOL_DEFINITIONS[0].description,
)
def list_datasources(
    ctx: McpContext,
) -> dict[str, Any]:
    """List datasources visible to the calling runtime identity."""

    return _run_runtime_tool(ctx, "list_datasources", {})


@runtime_mcp_server.tool(
    name="list_tags",
    description=RUNTIME_TOOL_DEFINITIONS[1].description,
)
def list_tags(
    ctx: McpContext,
) -> dict[str, Any]:
    """List tags visible to the calling runtime identity."""

    return _run_runtime_tool(ctx, "list_tags", {})


@runtime_mcp_server.tool(
    name="list_resources",
    description=RUNTIME_TOOL_DEFINITIONS[2].description,
)
def list_resources(
    ctx: McpContext,
    datasource_id: str,
) -> dict[str, Any]:
    """List readable resources under one datasource."""

    return _run_runtime_tool(
        ctx,
        "list_resources",
        {
            "datasource_id": datasource_id,
        },
    )


@runtime_mcp_server.tool(
    name="list_resources_by_tag",
    description=RUNTIME_TOOL_DEFINITIONS[3].description,
)
def list_resources_by_tag(
    ctx: McpContext,
    tag_names: list[str],
) -> dict[str, Any]:
    """List readable resources that match one or more tag names."""

    return _run_runtime_tool(
        ctx,
        "list_resources_by_tag",
        {
            "tag_names": tag_names,
        },
    )


@runtime_mcp_server.tool(
    name="describe_resource",
    description=RUNTIME_TOOL_DEFINITIONS[4].description,
)
def describe_resource(
    ctx: McpContext,
    resource_id: str,
) -> dict[str, Any]:
    """Describe one resource and its visible columns."""

    return _run_runtime_tool(
        ctx,
        "describe_resource",
        {
            "resource_id": resource_id,
        },
    )


@runtime_mcp_server.tool(
    name="preview_resource",
    description=RUNTIME_TOOL_DEFINITIONS[5].description,
)
def preview_resource(
    ctx: McpContext,
    resource_id: str,
    limit: int = 20,
) -> dict[str, Any]:
    """Preview rows from one resource with policy enforcement."""

    return _run_runtime_tool(
        ctx,
        "preview_resource",
        {
            "resource_id": resource_id,
            "limit": limit,
        },
    )


@runtime_mcp_server.tool(
    name="execute_query",
    description=RUNTIME_TOOL_DEFINITIONS[6].description,
)
def execute_query(
    ctx: McpContext,
    datasource_id: str,
    resource_ids: list[str],
    query: str,
    limit: int = 100,
) -> dict[str, Any]:
    """Run one guarded read-only SQL query."""

    return _run_runtime_tool(
        ctx,
        "execute_query",
        {
            "datasource_id": datasource_id,
            "resource_ids": resource_ids,
            "query": query,
            "limit": limit,
        },
    )
