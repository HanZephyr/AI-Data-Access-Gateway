import json
import secrets
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from adg.app.dependencies import AuthenticatedApiKey, require_admin_api_key
from adg.app.settings import get_settings
from adg.audit.models import AuditEvent
from adg.control_plane.db import get_session
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.governance import FieldPolicy, ResourcePolicy, ResourceTag, Tag
from adg.control_plane.models.masking import MaskingPolicy
from adg.control_plane.models.resource import Resource, ResourceField
from adg.shared.security import hash_api_key

router = APIRouter(prefix="/admin", tags=["admin-console"])


class TagRequest(BaseModel):
    """Payload for creating a governance tag."""

    name: str
    category: str | None = None
    description: str | None = None


class TagUpdateRequest(BaseModel):
    """Partial update payload for a governance tag."""

    name: str | None = None
    category: str | None = None
    description: str | None = None


class ResourceUpdateRequest(BaseModel):
    """Editable resource fields exposed by the admin console."""

    display_name: str | None = None
    query_language: str | None = None


class ResourceTagRequest(BaseModel):
    """Payload for attaching an existing tag to an existing resource."""

    tag_id: str
    resource_id: str


class ResourcePolicyRequest(BaseModel):
    """Payload for creating a resource-level policy."""

    subject_type: str
    subject_id: str
    effect: str
    action: str
    resource_id: str | None = None
    tag_id: str | None = None
    priority: int = 0
    status: str = "active"


class ResourcePolicyUpdateRequest(BaseModel):
    """Partial update payload for resource-level policies."""

    subject_type: str | None = None
    subject_id: str | None = None
    effect: str | None = None
    action: str | None = None
    resource_id: str | None = None
    tag_id: str | None = None
    priority: int | None = None
    status: str | None = None


class FieldPolicyRequest(BaseModel):
    """Payload for creating a field-level policy."""

    subject_type: str
    subject_id: str
    effect: str
    resource_id: str
    field_name: str
    action: str
    priority: int = 0
    status: str = "active"


class FieldPolicyUpdateRequest(BaseModel):
    """Partial update payload for field-level policies."""

    subject_type: str | None = None
    subject_id: str | None = None
    effect: str | None = None
    resource_id: str | None = None
    field_name: str | None = None
    action: str | None = None
    priority: int | None = None
    status: str | None = None


class MaskingPolicyRequest(BaseModel):
    """Payload for creating a field masking policy."""

    resource_id: str
    field_name: str
    strategy: str
    config: dict[str, object] = {}
    subject_type: str | None = None
    subject_id: str | None = None
    status: str = "active"


class MaskingPolicyUpdateRequest(BaseModel):
    """Partial update payload for masking policies."""

    resource_id: str | None = None
    field_name: str | None = None
    strategy: str | None = None
    config: dict[str, object] | None = None
    subject_type: str | None = None
    subject_id: str | None = None
    status: str | None = None


class ApiKeyCreateRequest(BaseModel):
    """Payload for minting a new API key."""

    name: str
    scopes: list[str]
    expires_at: datetime | None = None


class ApiKeyUpdateRequest(BaseModel):
    """Partial update payload for API key metadata."""

    name: str | None = None
    scopes: list[str] | None = None
    expires_at: datetime | None = None


@router.get("/resources")
def list_resources(
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
    datasource_id: str | None = None,
) -> list[dict[str, Any]]:
    """List resources, optionally filtered by datasource, for admin tables."""

    conditions = []
    if datasource_id is not None:
        conditions.append(Resource.datasource_id == datasource_id)
    resources = session.execute(
        select(Resource).where(*conditions).order_by(Resource.path)
    ).scalars()
    return [_serialize_resource(resource) for resource in resources]


@router.get("/resources/{resource_id}")
def get_resource(
    resource_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Fetch one resource by id."""

    resource = _get_by_id(session, Resource, resource_id, "Resource not found")
    return _serialize_resource(resource)


@router.patch("/resources/{resource_id}")
def update_resource(
    resource_id: str,
    payload: ResourceUpdateRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Update resource display metadata controlled by the admin console."""

    resource = _get_by_id(session, Resource, resource_id, "Resource not found")
    _apply_updates(resource, payload.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(resource)
    return _serialize_resource(resource)


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    """Delete a resource and dependent governance, field, and masking rows."""

    resource = _get_by_id(session, Resource, resource_id, "Resource not found")
    session.execute(delete(ResourceField).where(ResourceField.resource_id == resource_id))
    session.execute(delete(ResourceTag).where(ResourceTag.resource_id == resource_id))
    session.execute(delete(ResourcePolicy).where(ResourcePolicy.resource_id == resource_id))
    session.execute(delete(FieldPolicy).where(FieldPolicy.resource_id == resource_id))
    session.execute(delete(MaskingPolicy).where(MaskingPolicy.resource_id == resource_id))
    session.delete(resource)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/resources/{resource_id}/fields")
def list_resource_fields(
    resource_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    """List fields scanned for one resource."""

    fields = session.execute(
        select(ResourceField)
        .where(ResourceField.resource_id == resource_id)
        .order_by(ResourceField.ordinal_position)
    ).scalars()
    return [
        {
            "id": field.id,
            "resource_id": field.resource_id,
            "name": field.name,
            "data_type": field.data_type,
            "nullable": field.nullable,
            "ordinal_position": field.ordinal_position,
            "description": field.description,
        }
        for field in fields
    ]


@router.get("/tags")
def list_tags(
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    """List all governance tags."""

    tags = session.execute(
        select(Tag).order_by(Tag.name)
    ).scalars()
    return [_serialize_tag(tag) for tag in tags]


@router.post("/tags", status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Create a governance tag."""

    tag = Tag(**payload.model_dump())
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return _serialize_tag(tag)


@router.get("/tags/{tag_id}")
def get_tag(
    tag_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Fetch one tag by id."""

    tag = _get_by_id(session, Tag, tag_id, "Tag not found")
    return _serialize_tag(tag)


@router.patch("/tags/{tag_id}")
def update_tag(
    tag_id: str,
    payload: TagUpdateRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Update tag metadata."""

    tag = _get_by_id(session, Tag, tag_id, "Tag not found")
    _apply_updates(tag, payload.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(tag)
    return _serialize_tag(tag)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    """Delete a tag and any resource bindings that reference it."""

    session.execute(delete(ResourceTag).where(ResourceTag.tag_id == tag_id))
    tag = session.get(Tag, tag_id)
    if tag is not None:
        session.delete(tag)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/resource-tags", status_code=status.HTTP_201_CREATED)
def bind_resource_tag(
    payload: ResourceTagRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Attach a tag to a resource after validating the resource exists."""

    _require_resource(session, payload.resource_id)
    binding = ResourceTag(**payload.model_dump())
    session.add(binding)
    session.commit()
    session.refresh(binding)
    return {
        "id": binding.id,
        "tag_id": binding.tag_id,
        "resource_id": binding.resource_id,
    }


@router.get("/resource-policies")
def list_resource_policies(
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    """List resource-level policies with resource labels for display."""

    policies = session.execute(
        select(ResourcePolicy)
    ).scalars()
    return [_serialize_resource_policy(policy, session) for policy in policies]


@router.post("/resource-policies", status_code=status.HTTP_201_CREATED)
def create_resource_policy(
    payload: ResourcePolicyRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Create a resource-level policy, validating optional resource references."""

    if payload.resource_id is not None:
        _require_resource(session, payload.resource_id)
    policy = ResourcePolicy(**payload.model_dump())
    session.add(policy)
    session.commit()
    session.refresh(policy)
    return _serialize_resource_policy(policy, session)


@router.get("/resource-policies/{policy_id}")
def get_resource_policy(
    policy_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Fetch one resource-level policy."""

    policy = _get_by_id(session, ResourcePolicy, policy_id, "Policy not found")
    return _serialize_resource_policy(policy, session)


@router.patch("/resource-policies/{policy_id}")
def update_resource_policy(
    policy_id: str,
    payload: ResourcePolicyUpdateRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Update a resource-level policy."""

    policy = _get_by_id(session, ResourcePolicy, policy_id, "Policy not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("resource_id") is not None:
        _require_resource(session, data["resource_id"])
    _apply_updates(policy, data)
    session.commit()
    session.refresh(policy)
    return _serialize_resource_policy(policy, session)


@router.delete("/resource-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource_policy(
    policy_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    """Delete a resource-level policy."""

    _delete_by_id(session, ResourcePolicy, policy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/field-policies")
def list_field_policies(
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    """List field-level policies with resource labels for display."""

    policies = session.execute(
        select(FieldPolicy)
    ).scalars()
    return [_serialize_field_policy(policy, session) for policy in policies]


@router.post("/field-policies", status_code=status.HTTP_201_CREATED)
def create_field_policy(
    payload: FieldPolicyRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Create a field-level policy for an existing resource."""

    _require_resource(session, payload.resource_id)
    policy = FieldPolicy(**payload.model_dump())
    session.add(policy)
    session.commit()
    session.refresh(policy)
    return _serialize_field_policy(policy, session)


@router.get("/field-policies/{policy_id}")
def get_field_policy(
    policy_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Fetch one field-level policy."""

    policy = _get_by_id(session, FieldPolicy, policy_id, "Policy not found")
    return _serialize_field_policy(policy, session)


@router.patch("/field-policies/{policy_id}")
def update_field_policy(
    policy_id: str,
    payload: FieldPolicyUpdateRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Update a field-level policy."""

    policy = _get_by_id(session, FieldPolicy, policy_id, "Policy not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("resource_id") is not None:
        _require_resource(session, data["resource_id"])
    _apply_updates(policy, data)
    session.commit()
    session.refresh(policy)
    return _serialize_field_policy(policy, session)


@router.delete("/field-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field_policy(
    policy_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    """Delete a field-level policy."""

    _delete_by_id(session, FieldPolicy, policy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/masking-policies")
def list_masking_policies(
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    """List masking policies with decoded config and resource labels."""

    policies = session.execute(
        select(MaskingPolicy)
    ).scalars()
    return [_serialize_masking_policy(policy, session) for policy in policies]


@router.post("/masking-policies", status_code=status.HTTP_201_CREATED)
def create_masking_policy(
    payload: MaskingPolicyRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Create a masking policy with compact JSON config storage."""

    _require_resource(session, payload.resource_id)
    data = payload.model_dump()
    config = data.pop("config")
    policy = MaskingPolicy(config_json=json.dumps(config, separators=(",", ":")), **data)
    session.add(policy)
    session.commit()
    session.refresh(policy)
    return _serialize_masking_policy(policy, session)


@router.get("/masking-policies/{policy_id}")
def get_masking_policy(
    policy_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Fetch one masking policy."""

    policy = _get_by_id(session, MaskingPolicy, policy_id, "Masking policy not found")
    return _serialize_masking_policy(policy, session)


@router.patch("/masking-policies/{policy_id}")
def update_masking_policy(
    policy_id: str,
    payload: MaskingPolicyUpdateRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Update a masking policy and re-encode config when supplied."""

    policy = _get_by_id(session, MaskingPolicy, policy_id, "Masking policy not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("resource_id") is not None:
        _require_resource(session, data["resource_id"])
    config = data.pop("config", None)
    _apply_updates(policy, data)
    if config is not None:
        policy.config_json = json.dumps(config, separators=(",", ":"))
    session.commit()
    session.refresh(policy)
    return _serialize_masking_policy(policy, session)


@router.delete("/masking-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_masking_policy(
    policy_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    """Delete a masking policy."""

    _delete_by_id(session, MaskingPolicy, policy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api-keys")
def list_api_keys(
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    """List API key metadata without exposing raw key values."""

    keys = session.execute(select(ApiKey).order_by(ApiKey.created_at.desc())).scalars()
    return [_serialize_api_key(key) for key in keys]


@router.get("/api-keys/{api_key_id}")
def get_api_key(
    api_key_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Fetch one API key metadata record."""

    api_key = _get_by_id(session, ApiKey, api_key_id, "API key not found")
    return _serialize_api_key(api_key)


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreateRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Create an API key and return the raw value exactly once."""

    plaintext = f"adg_{secrets.token_urlsafe(24)}"
    api_key = ApiKey(
        name=payload.name,
        key_hash=hash_api_key(plaintext),
        status="active",
        scopes=json.dumps(payload.scopes, separators=(",", ":")),
        expires_at=payload.expires_at,
    )
    session.add(api_key)
    session.commit()
    session.refresh(api_key)
    return {**_serialize_api_key(api_key), "api_key": plaintext}


@router.patch("/api-keys/{api_key_id}")
def update_api_key(
    api_key_id: str,
    payload: ApiKeyUpdateRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Update API key metadata and status."""

    api_key = _get_by_id(session, ApiKey, api_key_id, "API key not found")
    data = payload.model_dump(exclude_unset=True)
    scopes = data.pop("scopes", None)
    _apply_updates(api_key, data)
    if scopes is not None:
        api_key.scopes = json.dumps(scopes, separators=(",", ":"))
    session.commit()
    session.refresh(api_key)
    return _serialize_api_key(api_key)


@router.post("/api-keys/{api_key_id}/revoke")
def revoke_api_key(
    api_key_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Disable an API key without deleting its audit history reference."""

    api_key = session.get(ApiKey, api_key_id)
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    api_key.status = "revoked"
    session.commit()
    session.refresh(api_key)
    return _serialize_api_key(api_key)


@router.get("/audit-events")
def list_audit_events(
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    """List audit events newest-first for the admin console."""

    events = session.execute(
        select(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
    ).scalars()
    return [_serialize_audit_event(event) for event in events]


@router.get("/mcp/setup")
def get_mcp_setup(
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
) -> dict[str, Any]:
    """Return minimal MCP HTTP facade setup information for operators."""

    return {
        "tool_url": "/mcp/tools/{tool_name}",
        "api_key_header": get_settings().api_key_header,
        "tools": [
            "list_datasources",
            "list_tags",
            "list_resources",
            "list_resources_by_tag",
            "describe_resource",
            "preview_resource",
            "execute_query",
        ],
    }


def _serialize_resource(resource: Resource) -> dict[str, Any]:
    """Convert a resource ORM object into a JSON-ready admin payload."""

    return {
        "id": resource.id,
        "datasource_id": resource.datasource_id,
        "kind": resource.kind,
        "name": resource.name,
        "path": resource.path,
        "display_name": resource.display_name,
        "query_language": resource.query_language,
        "scanned_at": resource.scanned_at.isoformat(),
    }


def _serialize_tag(tag: Tag) -> dict[str, Any]:
    """Convert a tag ORM object into a JSON-ready admin payload."""

    return {
        "id": tag.id,
        "name": tag.name,
        "category": tag.category,
        "description": tag.description,
    }


def _serialize_resource_policy(policy: ResourcePolicy, session: Session) -> dict[str, Any]:
    """Convert a resource policy into a JSON-ready payload with display labels."""

    return {
        "id": policy.id,
        "subject_type": policy.subject_type,
        "subject_id": policy.subject_id,
        "effect": policy.effect,
        "action": policy.action,
        "resource_label": _resource_label(session, policy.resource_id),
        "resource_id": policy.resource_id,
        "tag_id": policy.tag_id,
        "priority": policy.priority,
        "status": policy.status,
    }


def _serialize_field_policy(policy: FieldPolicy, session: Session) -> dict[str, Any]:
    """Convert a field policy into a JSON-ready payload with display labels."""

    return {
        "id": policy.id,
        "subject_type": policy.subject_type,
        "subject_id": policy.subject_id,
        "effect": policy.effect,
        "resource_label": _resource_label(session, policy.resource_id),
        "resource_id": policy.resource_id,
        "field_name": policy.field_name,
        "action": policy.action,
        "priority": policy.priority,
        "status": policy.status,
    }


def _serialize_masking_policy(policy: MaskingPolicy, session: Session) -> dict[str, Any]:
    """Convert a masking policy into a JSON-ready payload with decoded config."""

    return {
        "id": policy.id,
        "resource_label": _resource_label(session, policy.resource_id),
        "resource_id": policy.resource_id,
        "field_name": policy.field_name,
        "subject_type": policy.subject_type,
        "subject_id": policy.subject_id,
        "strategy": policy.strategy,
        "config": json.loads(policy.config_json),
        "status": policy.status,
    }


def _serialize_api_key(api_key: ApiKey) -> dict[str, Any]:
    """Return API key metadata safe for repeated display."""

    return {
        "id": api_key.id,
        "name": api_key.name,
        "status": api_key.status,
        "scopes": json.loads(api_key.scopes),
        "expires_at": None if api_key.expires_at is None else api_key.expires_at.isoformat(),
        "created_at": api_key.created_at.isoformat(),
    }


def _serialize_audit_event(event: AuditEvent) -> dict[str, Any]:
    """Decode audit JSON fields for admin-console display."""

    return {
        "id": event.id,
        "user_id": event.user_id,
        "api_key_id": event.api_key_id,
        "event_type": event.event_type,
        "datasource_id": event.datasource_id,
        "resource_ids": json.loads(event.resource_ids_json),
        "query_id": event.query_id,
        "sql_text": event.sql_text,
        "decision": event.decision,
        "reason": event.reason,
        "metadata": json.loads(event.metadata_json),
        "created_at": event.created_at.isoformat(),
    }


def _resource_label(session: Session, resource_id: str | None) -> str | None:
    """Build a human-readable resource label used by policy and masking tables."""

    if resource_id is None:
        return None
    resource = session.get(Resource, resource_id)
    if resource is None:
        return resource_id
    return f"{resource.display_name or resource.name} / {resource.path}"


def _get_by_id(session: Session, model: type[Any], item_id: str, detail: str) -> Any:
    """Load one ORM row or raise a FastAPI 404 with the supplied detail."""

    item = session.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return item


def _require_resource(session: Session, resource_id: str) -> Resource:
    """Validate that a referenced resource exists."""

    resource = session.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource


def _apply_updates(item: Any, data: dict[str, Any]) -> None:
    """Assign patch payload fields onto an ORM object."""

    for key, value in data.items():
        setattr(item, key, value)


def _delete_by_id(session: Session, model: type[Any], item_id: str) -> None:
    """Delete one ORM row by id and commit the change."""

    item = session.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    session.delete(item)
    session.commit()
