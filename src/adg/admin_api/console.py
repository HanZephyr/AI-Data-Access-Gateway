import json
import secrets
from datetime import UTC, datetime
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
    tenant_id: str
    name: str
    category: str | None = None
    description: str | None = None


class ResourceTagRequest(BaseModel):
    tenant_id: str
    tag_id: str
    resource_id: str


class ResourcePolicyRequest(BaseModel):
    tenant_id: str
    subject_type: str
    subject_id: str
    effect: str
    action: str
    resource_id: str | None = None
    tag_id: str | None = None
    priority: int = 0
    status: str = "active"


class FieldPolicyRequest(BaseModel):
    tenant_id: str
    subject_type: str
    subject_id: str
    effect: str
    resource_id: str
    field_name: str
    action: str
    priority: int = 0
    status: str = "active"


class MaskingPolicyRequest(BaseModel):
    tenant_id: str
    resource_id: str
    field_name: str
    strategy: str
    config: dict[str, object] = {}
    subject_type: str | None = None
    subject_id: str | None = None
    status: str = "active"


class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: list[str]
    expires_at: datetime | None = None


@router.get("/resources")
def list_resources(
    tenant_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
    datasource_id: str | None = None,
) -> list[dict[str, Any]]:
    conditions = [Resource.tenant_id == tenant_id]
    if datasource_id is not None:
        conditions.append(Resource.datasource_id == datasource_id)
    resources = session.execute(
        select(Resource).where(*conditions).order_by(Resource.path)
    ).scalars()
    return [_serialize_resource(resource) for resource in resources]


@router.get("/resources/{resource_id}/fields")
def list_resource_fields(
    resource_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
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
    tenant_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    tags = session.execute(select(Tag).where(Tag.tenant_id == tenant_id).order_by(Tag.name)).scalars()
    return [_serialize_tag(tag) for tag in tags]


@router.post("/tags", status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    tag = Tag(**payload.model_dump())
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return _serialize_tag(tag)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
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
    binding = ResourceTag(**payload.model_dump())
    session.add(binding)
    session.commit()
    session.refresh(binding)
    return {
        "id": binding.id,
        "tenant_id": binding.tenant_id,
        "tag_id": binding.tag_id,
        "resource_id": binding.resource_id,
    }


@router.get("/resource-policies")
def list_resource_policies(
    tenant_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    policies = session.execute(
        select(ResourcePolicy).where(ResourcePolicy.tenant_id == tenant_id)
    ).scalars()
    return [_serialize_resource_policy(policy) for policy in policies]


@router.post("/resource-policies", status_code=status.HTTP_201_CREATED)
def create_resource_policy(
    payload: ResourcePolicyRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    policy = ResourcePolicy(**payload.model_dump())
    session.add(policy)
    session.commit()
    session.refresh(policy)
    return _serialize_resource_policy(policy)


@router.delete("/resource-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource_policy(
    policy_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    _delete_by_id(session, ResourcePolicy, policy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/field-policies")
def list_field_policies(
    tenant_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    policies = session.execute(select(FieldPolicy).where(FieldPolicy.tenant_id == tenant_id)).scalars()
    return [_serialize_field_policy(policy) for policy in policies]


@router.post("/field-policies", status_code=status.HTTP_201_CREATED)
def create_field_policy(
    payload: FieldPolicyRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    policy = FieldPolicy(**payload.model_dump())
    session.add(policy)
    session.commit()
    session.refresh(policy)
    return _serialize_field_policy(policy)


@router.delete("/field-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field_policy(
    policy_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    _delete_by_id(session, FieldPolicy, policy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/masking-policies")
def list_masking_policies(
    tenant_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    policies = session.execute(
        select(MaskingPolicy).where(MaskingPolicy.tenant_id == tenant_id)
    ).scalars()
    return [_serialize_masking_policy(policy) for policy in policies]


@router.post("/masking-policies", status_code=status.HTTP_201_CREATED)
def create_masking_policy(
    payload: MaskingPolicyRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    data = payload.model_dump()
    config = data.pop("config")
    policy = MaskingPolicy(config_json=json.dumps(config, separators=(",", ":")), **data)
    session.add(policy)
    session.commit()
    session.refresh(policy)
    return _serialize_masking_policy(policy)


@router.delete("/masking-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_masking_policy(
    policy_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    _delete_by_id(session, MaskingPolicy, policy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api-keys")
def list_api_keys(
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    keys = session.execute(select(ApiKey).order_by(ApiKey.created_at.desc())).scalars()
    return [_serialize_api_key(key) for key in keys]


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreateRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
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


@router.post("/api-keys/{api_key_id}/revoke")
def revoke_api_key(
    api_key_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    api_key = session.get(ApiKey, api_key_id)
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    api_key.status = "revoked"
    session.commit()
    session.refresh(api_key)
    return _serialize_api_key(api_key)


@router.get("/audit-events")
def list_audit_events(
    tenant_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    events = session.execute(
        select(AuditEvent)
        .where(AuditEvent.tenant_id == tenant_id)
        .order_by(AuditEvent.created_at.desc())
    ).scalars()
    return [_serialize_audit_event(event) for event in events]


@router.get("/mcp/setup")
def get_mcp_setup(
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
) -> dict[str, Any]:
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
    return {
        "id": resource.id,
        "tenant_id": resource.tenant_id,
        "datasource_id": resource.datasource_id,
        "kind": resource.kind,
        "name": resource.name,
        "path": resource.path,
        "display_name": resource.display_name,
        "query_language": resource.query_language,
        "scanned_at": resource.scanned_at.isoformat(),
    }


def _serialize_tag(tag: Tag) -> dict[str, Any]:
    return {
        "id": tag.id,
        "tenant_id": tag.tenant_id,
        "name": tag.name,
        "category": tag.category,
        "description": tag.description,
    }


def _serialize_resource_policy(policy: ResourcePolicy) -> dict[str, Any]:
    return {
        "id": policy.id,
        "tenant_id": policy.tenant_id,
        "subject_type": policy.subject_type,
        "subject_id": policy.subject_id,
        "effect": policy.effect,
        "action": policy.action,
        "resource_id": policy.resource_id,
        "tag_id": policy.tag_id,
        "priority": policy.priority,
        "status": policy.status,
    }


def _serialize_field_policy(policy: FieldPolicy) -> dict[str, Any]:
    return {
        "id": policy.id,
        "tenant_id": policy.tenant_id,
        "subject_type": policy.subject_type,
        "subject_id": policy.subject_id,
        "effect": policy.effect,
        "resource_id": policy.resource_id,
        "field_name": policy.field_name,
        "action": policy.action,
        "priority": policy.priority,
        "status": policy.status,
    }


def _serialize_masking_policy(policy: MaskingPolicy) -> dict[str, Any]:
    return {
        "id": policy.id,
        "tenant_id": policy.tenant_id,
        "resource_id": policy.resource_id,
        "field_name": policy.field_name,
        "subject_type": policy.subject_type,
        "subject_id": policy.subject_id,
        "strategy": policy.strategy,
        "config": json.loads(policy.config_json),
        "status": policy.status,
    }


def _serialize_api_key(api_key: ApiKey) -> dict[str, Any]:
    return {
        "id": api_key.id,
        "name": api_key.name,
        "status": api_key.status,
        "scopes": json.loads(api_key.scopes),
        "expires_at": None if api_key.expires_at is None else api_key.expires_at.isoformat(),
        "created_at": api_key.created_at.isoformat(),
    }


def _serialize_audit_event(event: AuditEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "tenant_id": event.tenant_id,
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


def _delete_by_id(session: Session, model: type[Any], item_id: str) -> None:
    item = session.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    session.delete(item)
    session.commit()
