from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from adg.control_plane.imports.excel import normalize_excel_import_rows, normalize_org_path
from adg.control_plane.imports.models import ExcelImportExecution, ExcelImportPreview
from adg.control_plane.models.directory import OrgNode, Role, User, UserRole
from adg.control_plane.services.api_key_service import create_api_key

ROOT_ORG_NAME = "Root"
ROOT_ORG_PATH = ""


def preview_excel_import(
    session: Session,
    *,
    rows: list[dict[str, object]],
    delimiter: str = "/",
) -> ExcelImportPreview:
    """Preview directory changes for a structured Excel import batch."""

    normalized_rows = normalize_excel_import_rows(rows, delimiter=delimiter)
    existing_paths = set(session.execute(select(OrgNode.path)).scalars())
    existing_role_names = set(session.execute(select(Role.name)).scalars())
    existing_external_refs = set(session.execute(select(User.external_ref)).scalars())

    org_nodes_to_create: list[str] = []
    roles_to_create: list[str] = []
    pending_paths = set(existing_paths)
    pending_roles = set(existing_role_names)
    users: list[dict[str, object]] = []
    create_count = 0
    update_count = 0
    root_org_node_required = False

    for row in normalized_rows:
        users.append(
            {
                "user_name": row.user_name,
                "external_ref": row.external_ref,
                "org_path": row.org_path,
                "roles": list(row.roles),
                "action": "update" if row.external_ref in existing_external_refs else "create",
            }
        )
        if row.external_ref in existing_external_refs:
            update_count += 1
        else:
            create_count += 1

        if row.org_path is None:
            if ROOT_ORG_PATH not in pending_paths:
                root_org_node_required = True
            continue

        current_segments: list[str] = []
        for segment in normalize_org_path(row.org_path, delimiter):
            current_segments.append(segment)
            path = delimiter.join(current_segments)
            if path not in pending_paths:
                org_nodes_to_create.append(path)
                pending_paths.add(path)

        for role_name in row.roles:
            if role_name not in pending_roles:
                roles_to_create.append(role_name)
                pending_roles.add(role_name)

    return ExcelImportPreview(
        users=users,
        org_nodes_to_create=org_nodes_to_create,
        roles_to_create=roles_to_create,
        root_org_node_required=root_org_node_required,
        summary={"create_count": create_count, "update_count": update_count},
    )


def execute_excel_import(
    session: Session,
    *,
    rows: list[dict[str, object]],
    delimiter: str = "/",
) -> ExcelImportExecution:
    """Apply a structured Excel import batch to users, org nodes, and roles."""

    normalized_rows = normalize_excel_import_rows(rows, delimiter=delimiter)
    org_nodes_by_path = {
        node.path: node for node in session.execute(select(OrgNode).order_by(OrgNode.depth)).scalars()
    }
    roles_by_name = {role.name: role for role in session.execute(select(Role)).scalars()}
    users_by_external_ref = {
        user.external_ref: user for user in session.execute(select(User)).scalars()
    }
    users: list[dict[str, object]] = []
    org_nodes_created: list[str] = []
    roles_created: list[str] = []
    created_users = 0
    updated_users = 0
    runtime_keys_created = 0
    root_org_node_created = False

    for row in normalized_rows:
        org_node = _resolve_org_node(
            session,
            row.org_path,
            delimiter,
            org_nodes_by_path,
            org_nodes_created,
        )
        if row.org_path is None and org_node.path == ROOT_ORG_PATH and ROOT_ORG_PATH in org_nodes_created:
            root_org_node_created = True
        role_ids = _resolve_roles(session, row.roles, roles_by_name, roles_created)
        user = users_by_external_ref.get(row.external_ref)
        runtime_key_created = False
        action: str

        if user is None:
            user = User(
                name=row.user_name,
                external_ref=row.external_ref,
                org_node_id=org_node.id,
                status="active",
            )
            session.add(user)
            session.flush()
            _replace_roles(session, user.id, role_ids)
            create_api_key(
                session,
                name=f"user:{user.name}",
                scopes=["runtime"],
                user_id=user.id,
            )
            users_by_external_ref[user.external_ref] = user
            created_users += 1
            runtime_keys_created += 1
            runtime_key_created = True
            action = "create"
        else:
            user.name = row.user_name
            user.org_node_id = org_node.id
            user.status = "active"
            _replace_roles(session, user.id, role_ids)
            updated_users += 1
            action = "update"

        users.append(
            {
                "user_name": user.name,
                "external_ref": user.external_ref,
                "org_path": row.org_path,
                "roles": list(row.roles),
                "action": action,
                "user_id": user.id,
                "runtime_key_created": runtime_key_created,
            }
        )

    return ExcelImportExecution(
        users=users,
        org_nodes_created=org_nodes_created,
        roles_created=roles_created,
        root_org_node_created=root_org_node_created,
        summary={
            "created_users": created_users,
            "updated_users": updated_users,
            "runtime_keys_created": runtime_keys_created,
        },
    )


def _resolve_org_node(
    session: Session,
    org_path: str | None,
    delimiter: str,
    org_nodes_by_path: dict[str, OrgNode],
    org_nodes_created: list[str],
) -> OrgNode:
    if org_path is None:
        return _ensure_root_org_node(session, org_nodes_by_path, org_nodes_created)

    current_segments: list[str] = []
    parent: OrgNode | None = None
    for depth, segment in enumerate(normalize_org_path(org_path, delimiter)):
        current_segments.append(segment)
        path = delimiter.join(current_segments)
        node = org_nodes_by_path.get(path)
        if node is None:
            node = OrgNode(
                name=segment,
                parent_id=None if parent is None else parent.id,
                path=path,
                depth=depth,
                status="active",
            )
            session.add(node)
            session.flush()
            org_nodes_by_path[path] = node
            org_nodes_created.append(path)
        parent = node

    if parent is None:
        return _ensure_root_org_node(session, org_nodes_by_path, org_nodes_created)
    return parent


def _ensure_root_org_node(
    session: Session,
    org_nodes_by_path: dict[str, OrgNode],
    org_nodes_created: list[str],
) -> OrgNode:
    root = org_nodes_by_path.get(ROOT_ORG_PATH)
    if root is None:
        root = OrgNode(
            name=ROOT_ORG_NAME,
            parent_id=None,
            path=ROOT_ORG_PATH,
            depth=0,
            status="active",
        )
        session.add(root)
        session.flush()
        org_nodes_by_path[ROOT_ORG_PATH] = root
        org_nodes_created.append(ROOT_ORG_PATH)
    return root


def _resolve_roles(
    session: Session,
    role_names: list[str],
    roles_by_name: dict[str, Role],
    roles_created: list[str],
) -> list[str]:
    role_ids: list[str] = []
    for role_name in role_names:
        role = roles_by_name.get(role_name)
        if role is None:
            role = Role(name=role_name, status="active")
            session.add(role)
            session.flush()
            roles_by_name[role_name] = role
            roles_created.append(role_name)
        role_ids.append(role.id)
    return role_ids


def _replace_roles(session: Session, user_id: str, role_ids: list[str]) -> None:
    session.execute(delete(UserRole).where(UserRole.user_id == user_id))
    for role_id in role_ids:
        session.add(UserRole(user_id=user_id, role_id=role_id))
    session.flush()
