import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.app.settings import get_settings
from adg.control_plane.db import get_session
from adg.control_plane.models.api_key import ApiKey
from adg.shared.security import verify_api_key


@dataclass(frozen=True)
class AuthenticatedApiKey:
    """Minimal authenticated API-key identity shared by request handlers."""

    id: str
    scopes: str


def _normalize_expiration(expires_at: datetime) -> datetime:
    """Treat legacy naive timestamps as UTC before comparing them."""

    if expires_at.tzinfo is None:
        return expires_at.replace(tzinfo=UTC)
    return expires_at


def require_api_key(
    session: Annotated[Session, Depends(get_session)],
    request: Request,
) -> AuthenticatedApiKey:
    """Authenticate a request against active API keys stored in the control plane."""

    raw_api_key = request.headers.get(get_settings().api_key_header)
    if raw_api_key is None or raw_api_key == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    api_keys = session.execute(select(ApiKey).where(ApiKey.status == "active")).scalars()

    # API keys are hashed, so the request key must be checked against each active hash.
    for api_key in api_keys:
        if verify_api_key(raw_api_key, api_key.key_hash):
            if api_key.expires_at is not None and _normalize_expiration(
                api_key.expires_at
            ) <= datetime.now(UTC):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Expired API key",
                )
            return AuthenticatedApiKey(id=api_key.id, scopes=api_key.scopes)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


def require_admin_api_key(
    api_key: Annotated[AuthenticatedApiKey, Depends(require_api_key)],
) -> AuthenticatedApiKey:
    """Require the authenticated API key to carry the admin scope."""

    if "admin" not in json.loads(api_key.scopes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin scope required",
        )

    return api_key


def require_runtime_api_key(
    api_key: Annotated[AuthenticatedApiKey, Depends(require_api_key)],
) -> AuthenticatedApiKey:
    """Require the authenticated API key to carry the runtime scope."""

    if "runtime" not in json.loads(api_key.scopes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Runtime scope required",
        )

    return api_key
