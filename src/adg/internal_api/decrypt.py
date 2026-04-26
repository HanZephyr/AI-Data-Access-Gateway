import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.app.dependencies import AuthenticatedRuntimeKey, require_runtime_api_key
from adg.app.settings import get_settings
from adg.audit.service import AuditService
from adg.control_plane.db import get_session
from adg.control_plane.models.resource import Resource
from adg.masking.service import MaskingService
from adg.policy.runtime import RuntimePolicyService
from adg.shared.errors import ValidationError

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.post("/decrypt")
def decrypt_values(
    payload: dict[str, Any],
    session: Annotated[Session, Depends(get_session)],
    api_key: Annotated[AuthenticatedRuntimeKey, Depends(require_runtime_api_key)],
) -> dict[str, list[str]]:
    """Decrypt reversible masking markers for the authenticated runtime user."""

    user_id = api_key.user_id
    values = [str(value) for value in payload.get("values", [])]
    masking_service = MaskingService(session, secret_key=get_settings().secret_key)
    policy = RuntimePolicyService(session)
    try:
        contexts = masking_service.get_decrypt_contexts(user_id=user_id, values=values)
        resource_ids = sorted(
            {
                resource_id
                for context in contexts
                for resource_id in json.loads(context.resource_ids_json)
            }
        )
        if not resource_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Decrypt context is missing resource scope",
            )
        resources = list(
            session.execute(select(Resource).where(Resource.id.in_(resource_ids))).scalars()
        )
        for resource in resources:
            decision = policy.check_decrypt_access(
                identity=api_key.runtime_identity,
                resource=resource,
            )
            if not decision.allowed:
                AuditService(session).record_event(
                    user_id=user_id,
                    api_key_id=api_key.id,
                    event_type="decryption",
                    decision="denied",
                    datasource_id=resource.datasource_id,
                    resource_ids=[resource.id],
                    query_id=None,
                    sql_text=None,
                    reason=decision.reason,
                    metadata={"value_count": len(values)},
                )
                session.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Decrypt not allowed for this resource",
                )

        plaintext = masking_service.decrypt_values(user_id=user_id, values=values)
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    datasource_ids = {resource.datasource_id for resource in resources}
    datasource_id = next(iter(datasource_ids)) if len(datasource_ids) == 1 else None
    AuditService(session).record_event(
        user_id=user_id,
        api_key_id=api_key.id,
        event_type="decryption",
        decision="allowed",
        datasource_id=datasource_id,
        resource_ids=resource_ids,
        query_id=None,
        sql_text=None,
        reason=None,
        metadata={"value_count": len(values)},
    )
    session.commit()
    return {"values": plaintext}
