from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.control_plane.db import get_session
from adg.control_plane.models.api_key import ApiKey
from adg.shared.security import verify_api_key


@dataclass(frozen=True)
class AuthenticatedApiKey:
    id: str
    scopes: str


def require_api_key(
    session: Annotated[Session, Depends(get_session)],
    raw_api_key: Annotated[str | None, Header(alias="X-ADG-API-Key")] = None,
) -> AuthenticatedApiKey:
    if raw_api_key is None or raw_api_key == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    api_keys = session.execute(select(ApiKey).where(ApiKey.status == "active")).scalars()

    for api_key in api_keys:
        if verify_api_key(raw_api_key, api_key.key_hash):
            return AuthenticatedApiKey(id=api_key.id, scopes=api_key.scopes)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )
