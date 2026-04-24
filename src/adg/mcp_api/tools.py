from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from adg.app.dependencies import AuthenticatedApiKey, require_api_key
from adg.control_plane.db import get_session
from adg.gateway_runtime.tools import GatewayRuntimeService
from adg.policy.runtime import IdentityContext

router = APIRouter(prefix="/mcp/tools", tags=["mcp"])


@router.post("/{tool_name}")
def call_tool(
    tool_name: str,
    payload: dict[str, Any],
    session: Annotated[Session, Depends(get_session)],
    api_key: Annotated[AuthenticatedApiKey, Depends(require_api_key)],
) -> dict[str, Any]:
    identity = _identity_from_payload(payload)
    runtime = GatewayRuntimeService(session)

    if tool_name == "list_datasources":
        return runtime.list_datasources(identity=identity, api_key_id=api_key.id)
    if tool_name == "list_tags":
        return runtime.list_tags(identity=identity, api_key_id=api_key.id)
    if tool_name == "list_resources":
        return runtime.list_resources(
            identity=identity,
            api_key_id=api_key.id,
            datasource_id=str(payload["datasource_id"]),
        )
    if tool_name == "list_resources_by_tag":
        return runtime.list_resources_by_tag(
            identity=identity,
            api_key_id=api_key.id,
            tag_names=[str(item) for item in payload.get("tag_names", [])],
        )
    if tool_name == "describe_resource":
        return runtime.describe_resource(
            identity=identity,
            api_key_id=api_key.id,
            resource_id=str(payload["resource_id"]),
        )
    if tool_name == "preview_resource":
        return runtime.preview_resource(
            identity=identity,
            api_key_id=api_key.id,
            resource_id=str(payload["resource_id"]),
            limit=int(payload.get("limit", 20)),
        )
    if tool_name == "execute_query":
        return runtime.execute_query(
            identity=identity,
            api_key_id=api_key.id,
            datasource_id=str(payload["datasource_id"]),
            resource_ids=[str(item) for item in payload.get("resource_ids", [])],
            query=str(payload["query"]),
            limit=int(payload.get("limit", 100)),
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Unknown MCP tool",
    )


def _identity_from_payload(payload: dict[str, Any]) -> IdentityContext:
    try:
        tenant_id = str(payload["tenant_id"])
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tenant_id is required",
        ) from error

    return IdentityContext(
        tenant_id=tenant_id,
        user_id=None if payload.get("user_id") is None else str(payload["user_id"]),
        roles=[str(item) for item in payload.get("roles", [])],
        groups=[str(item) for item in payload.get("groups", [])],
    )
