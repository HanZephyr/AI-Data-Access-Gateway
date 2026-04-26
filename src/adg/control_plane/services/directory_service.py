import json
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.directory import OrgNode, Role, User, UserRole
from adg.control_plane.services.api_key_service import create_api_key

_UNSET = object()


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


@dataclass(slots=True)
class OrgNodeSummary:
    """Tree-friendly organization payload used by the admin console."""

    id: str
    name: str
    code: str | None
    parent_id: str | None
    path: str
    depth: int
    status: str
    direct_user_count: int
    direct_user_names: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "parent_id": self.parent_id,
            "path": self.path,
            "depth": self.depth,
            "status": self.status,
            "direct_user_count": self.direct_user_count,
            "direct_user_names": list(self.direct_user_names),
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
        org_path_by_id: dict[str, str] = {}
        if org_node_ids:
            org_path_rows = self._session.execute(
                select(OrgNode.id, OrgNode.path).where(OrgNode.id.in_(org_node_ids))
            ).all()
            org_path_by_id = {row[0]: row[1] for row in org_path_rows}

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
                org_path=(
                    org_path_by_id.get(user.org_node_id)
                    if user.org_node_id is not None
                    else None
                ),
                role_ids=role_ids_by_user_id.get(user.id, []),
                role_names=role_names_by_user_id.get(user.id, []),
                status=user.status,
                runtime_key_status=runtime_key_status_by_user_id.get(user.id, "missing"),
            )
            for user in users
        ]

    def create_org_node(
        self,
        *,
        name: str,
        parent_id: str | None,
        code: str | None = None,
        status: str = "active",
    ) -> OrgNode:
        parent = self._session.get(OrgNode, parent_id) if parent_id else None
        path = self._build_org_path(name, parent.path if parent is not None else None)
        node = OrgNode(
            name=name,
            code=code,
            parent_id=parent_id,
            path=path,
            depth=0 if parent is None else parent.depth + 1,
            status=status,
        )
        self._session.add(node)
        self._session.flush()
        return node

    def update_org_node(
        self,
        node_id: str,
        *,
        name: str | None = None,
        parent_id: str | None | object = _UNSET,
        code: str | None | object = _UNSET,
        status: str | None = None,
    ) -> OrgNode:
        node = self._session.execute(select(OrgNode).where(OrgNode.id == node_id)).scalar_one()
        resolved_parent_id = node.parent_id if parent_id is _UNSET else parent_id
        parent = self._session.get(OrgNode, resolved_parent_id) if resolved_parent_id else None
        if parent is not None and self._is_descendant(parent.id, node.id):
            raise ValueError("Organization nodes cannot be moved underneath their descendants")

        original_path = node.path
        original_depth = node.depth

        if name is not None:
            node.name = name.strip()
        if code is not _UNSET:
            if isinstance(code, str):
                node.code = code.strip() or None
            else:
                node.code = None
        if status is not None:
            node.status = status
        if parent_id is not _UNSET:
            node.parent_id = resolved_parent_id if isinstance(resolved_parent_id, str) else None

        parent_path = parent.path if parent is not None else None
        node.path = self._build_org_path(node.name, parent_path)
        node.depth = 0 if parent is None else parent.depth + 1
        if node.path != original_path or node.depth != original_depth:
            self._update_descendant_paths(
                node.id,
                original_path,
                node.path,
                original_depth,
                node.depth,
            )
        self._session.flush()
        return node

    def delete_org_node(self, node_id: str) -> None:
        node = self._session.execute(select(OrgNode).where(OrgNode.id == node_id)).scalar_one()
        child = self._session.execute(
            select(OrgNode.id).where(OrgNode.parent_id == node_id)
        ).scalar_one_or_none()
        if child is not None:
            raise ValueError("Delete child organization nodes before removing this node")
        direct_user = self._session.execute(
            select(User.id).where(User.org_node_id == node_id)
        ).scalar_one_or_none()
        if direct_user is not None:
            raise ValueError("Move or disable users before removing this node")
        self._session.delete(node)
        self._session.flush()

    def list_org_nodes(self) -> list[OrgNodeSummary]:
        nodes = list(self._session.execute(select(OrgNode).order_by(OrgNode.path)).scalars())
        if not nodes:
            return []

        node_ids = [node.id for node in nodes]
        direct_users_by_node_id: dict[str, list[str]] = defaultdict(list)
        user_rows = self._session.execute(
            select(User.org_node_id, User.name)
            .where(User.org_node_id.in_(node_ids))
            .order_by(User.name, User.id)
        ).all()
        for org_node_id, user_name in user_rows:
            if org_node_id is None:
                continue
            direct_users_by_node_id[org_node_id].append(user_name)

        return [
            OrgNodeSummary(
                id=node.id,
                name=node.name,
                code=node.code,
                parent_id=node.parent_id,
                path=node.path,
                depth=node.depth,
                status=node.status,
                direct_user_count=len(direct_users_by_node_id.get(node.id, [])),
                direct_user_names=direct_users_by_node_id.get(node.id, []),
            )
            for node in nodes
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

    def _build_org_path(self, name: str, parent_path: str | None) -> str:
        clean_name = name.strip()
        return clean_name if not parent_path else f"{parent_path}/{clean_name}"

    def _is_descendant(self, candidate_id: str, ancestor_id: str) -> bool:
        current_id = candidate_id
        while current_id:
            if current_id == ancestor_id:
                return True
            current = self._session.get(OrgNode, current_id)
            if current is None or current.parent_id is None:
                break
            current_id = current.parent_id
        return False

    def _update_descendant_paths(
        self,
        node_id: str,
        original_path: str,
        new_path: str,
        original_depth: int,
        new_depth: int,
    ) -> None:
        descendants = list(
            self._session.execute(
                select(OrgNode)
                .where(OrgNode.path.like(f"{original_path}/%"))
                .order_by(OrgNode.depth, OrgNode.path)
            ).scalars()
        )
        depth_delta = new_depth - original_depth
        for descendant in descendants:
            suffix = descendant.path[len(original_path):]
            descendant.path = f"{new_path}{suffix}"
            descendant.depth = descendant.depth + depth_delta
