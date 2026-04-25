import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.app.settings import get_settings
from adg.control_plane.db import get_session
from adg.control_plane.models.api_key import ApiKey
from adg.policy.runtime import IdentityContext, load_runtime_identity_for_user
from adg.shared.security import verify_api_key


@dataclass(frozen=True)
class AuthenticatedApiKey:
    """Minimal authenticated API-key identity shared by request handlers."""

    id: str
    scopes: str
    user_id: str | None = None


@dataclass(frozen=True)
class AuthenticatedRuntimeKey(AuthenticatedApiKey):
    """Runtime-scoped API key with directory identity loaded from the key binding."""

    role_ids: list[str] = field(default_factory=list)
    org_node_id: str | None = None

    @property
    def runtime_identity(self) -> IdentityContext:
        """Return the key-derived runtime identity used by shared tool dispatch."""

        return IdentityContext(
            user_id=self.user_id,
            roles=list(self.role_ids),
            org_node_id=self.org_node_id,
        )


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
    return authenticate_api_key_value(session, raw_api_key)


def authenticate_api_key_value(
    session: Session,
    raw_api_key: str | None,
) -> AuthenticatedApiKey:
    """Authenticate one raw API key value against the active control-plane keys."""

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
            return AuthenticatedApiKey(
                id=api_key.id,
                scopes=api_key.scopes,
                user_id=api_key.user_id,
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


def require_admin_api_key(
    api_key: Annotated[AuthenticatedApiKey, Depends(require_api_key)],
) -> AuthenticatedApiKey:
    """Require the authenticated API key to carry the admin scope."""

    return require_scope(api_key, "admin", "Admin scope required")


def require_runtime_api_key(
    session: Annotated[Session, Depends(get_session)],
    request: Request,
) -> AuthenticatedRuntimeKey:
    """Require one runtime-scoped API key and load its bound runtime identity."""

    raw_api_key = request.headers.get(get_settings().api_key_header)
    return authenticate_runtime_api_key_value(session, raw_api_key)


def require_scope(
    api_key: AuthenticatedApiKey,
    scope: str,
    detail: str,
) -> AuthenticatedApiKey:
    """Require one authenticated API key to include a specific scope."""

    if scope not in json.loads(api_key.scopes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )

    return api_key


def authenticate_runtime_api_key_value(
    session: Session,
    raw_api_key: str | None,
) -> AuthenticatedRuntimeKey:
    """Authenticate one raw API key value and require the runtime scope."""

    authenticated = require_scope(
        authenticate_api_key_value(session, raw_api_key),
        "runtime",
        "Runtime scope required",
    )
    identity = load_runtime_identity_for_user(session, user_id=authenticated.user_id)
    return AuthenticatedRuntimeKey(
        id=authenticated.id,
        scopes=authenticated.scopes,
        user_id=identity.user_id,
        role_ids=list(identity.role_ids),
        org_node_id=identity.org_node_id,
    )
