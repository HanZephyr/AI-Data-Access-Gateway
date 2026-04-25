import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.directory import User, UserRole
from adg.control_plane.services.api_key_service import create_api_key


class DirectoryService:
    """Manage directory users and their single active runtime API key."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_user(
        self,
        *,
        name: str,
        external_ref: str,
        org_node_id: str | None,
        role_ids: list[str],
    ) -> tuple[User, str]:
        user = User(
            name=name,
            external_ref=external_ref,
            org_node_id=org_node_id,
            status="active",
        )
        self._session.add(user)
        self._session.flush()
        self._replace_roles(user.id, role_ids)
        _, plaintext = create_api_key(
            self._session,
            name=f"user:{user.name}",
            scopes=["runtime"],
            user_id=user.id,
        )
        return user, plaintext

    def reset_runtime_key(self, user_id: str) -> str:
        self._session.execute(select(User).where(User.id == user_id)).scalar_one()
        self._revoke_active_runtime_keys(user_id)
        _, plaintext = create_api_key(
            self._session,
            name=f"user:{user_id}",
            scopes=["runtime"],
            user_id=user_id,
        )
        return plaintext

    def _replace_roles(self, user_id: str, role_ids: list[str]) -> None:
        if not role_ids:
            return
        for role_id in role_ids:
            self._session.add(UserRole(user_id=user_id, role_id=role_id))

    def _revoke_active_runtime_keys(self, user_id: str) -> None:
        active_keys = self._session.execute(
            select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.status == "active")
        ).scalars()
        for key in active_keys:
            if "runtime" in json.loads(key.scopes):
                key.status = "revoked"
        self._session.flush()
