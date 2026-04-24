import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from adg.app.dependencies import AuthenticatedApiKey, require_api_key
from adg.app.settings import get_settings
from adg.audit.service import AuditService
from adg.control_plane.db import get_session
from adg.masking.service import MaskingService
from adg.shared.errors import ValidationError

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/decrypt")
def decrypt_values(
    payload: dict[str, Any],
    session: Annotated[Session, Depends(get_session)],
    api_key: Annotated[AuthenticatedApiKey, Depends(require_api_key)],
) -> dict[str, list[str]]:
    if "internal" not in json.loads(api_key.scopes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Internal scope required",
        )

    tenant_id = str(payload["tenant_id"])
    user_id = None if payload.get("user_id") is None else str(payload["user_id"])
    values = [str(value) for value in payload.get("values", [])]
    try:
        plaintext = MaskingService(
            session,
            secret_key=get_settings().secret_key,
        ).decrypt_values(tenant_id=tenant_id, user_id=user_id, values=values)
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    AuditService(session).record_event(
        tenant_id=tenant_id,
        user_id=user_id,
        api_key_id=api_key.id,
        event_type="decryption",
        decision="allowed",
        datasource_id=None,
        resource_ids=[],
        query_id=None,
        sql_text=None,
        reason=None,
        metadata={"value_count": len(values)},
    )
    session.commit()
    return {"values": plaintext}
