import json
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.directory import OrgNode, Role, User, UserRole
from adg.control_plane.services.api_key_service import create_api_key


@dataclass(slots=True)
class DirectoryUserSummary:
    """Flattened directory user payload used by admin APIs and console tables."""

    id: str
    name: str
    external_ref: str
    org_node_id: str | None
    org_path: str | None
    role_ids: list[str]
    role_names: list[str]
    status: str
    runtime_key_status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "external_ref": self.external_ref,
            "org_node_id": self.org_node_id,
            "org_path": self.org_path,
            "role_ids": list(self.role_ids),
            "role_names": list(self.role_names),
            "status": self.status,
            "runtime_key_status": self.runtime_key_status,
        }


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

    def list_users(self) -> list[DirectoryUserSummary]:
        users = list(self._session.execute(select(User).order_by(User.name, User.id)).scalars())
        if not users:
            return []

        user_ids = [user.id for user in users]
        org_node_ids = sorted({user.org_node_id for user in users if user.org_node_id is not None})
        org_path_by_id = (
            dict(
                self._session.execute(
                    select(OrgNode.id, OrgNode.path).where(OrgNode.id.in_(org_node_ids))
                ).all()
            )
            if org_node_ids
            else {}
        )

        role_ids_by_user_id: dict[str, list[str]] = defaultdict(list)
        role_names_by_user_id: dict[str, list[str]] = defaultdict(list)
        role_rows = self._session.execute(
            select(UserRole.user_id, Role.id, Role.name)
            .join(Role, Role.id == UserRole.role_id)
            .where(UserRole.user_id.in_(user_ids))
            .order_by(UserRole.user_id, Role.name, Role.id)
        ).all()
        for user_id, role_id, role_name in role_rows:
            role_ids_by_user_id[user_id].append(role_id)
            role_names_by_user_id[user_id].append(role_name)

        runtime_key_status_by_user_id = {user_id: "missing" for user_id in user_ids}
        runtime_key_rows = self._session.execute(
            select(ApiKey.user_id, ApiKey.scopes)
            .where(ApiKey.user_id.in_(user_ids), ApiKey.status == "active")
            .order_by(ApiKey.created_at.desc())
        ).all()
        for user_id, scopes_json in runtime_key_rows:
            if user_id is None:
                continue
            if "runtime" in json.loads(scopes_json):
                runtime_key_status_by_user_id[user_id] = "active"

        return [
            DirectoryUserSummary(
                id=user.id,
                name=user.name,
                external_ref=user.external_ref,
                org_node_id=user.org_node_id,
                org_path=org_path_by_id.get(user.org_node_id) if user.org_node_id is not None else None,
                role_ids=role_ids_by_user_id.get(user.id, []),
                role_names=role_names_by_user_id.get(user.id, []),
                status=user.status,
                runtime_key_status=runtime_key_status_by_user_id.get(user.id, "missing"),
            )
            for user in users
        ]

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
