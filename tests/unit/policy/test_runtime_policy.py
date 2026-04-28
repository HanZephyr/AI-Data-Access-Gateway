import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from adg.app.dependencies import authenticate_runtime_api_key_value
from adg.control_plane.models.api_key import ApiKey
from adg.control_plane.models.directory import OrgNode, Role, User, UserRole
from adg.control_plane.models.governance import FieldPolicy, ResourcePolicy, ResourceTag, Tag
from adg.control_plane.models.resource import Resource
from adg.policy.runtime import IdentityContext, RuntimePolicyService
from adg.shared.security import hash_api_key


def add_resource(
    *,
    db_session: Session,
    resource_id: str,
    datasource_id: str = "ds_1",
    path: str = "warehouse.public.customers",
    parent_id: str | None = None,
    kind: str = "relational_table",
) -> Resource:
    resource = Resource(
        id=resource_id,
        datasource_id=datasource_id,
        parent_id=parent_id,
        kind=kind,
        name=path.rsplit(".", 1)[-1],
        path=path,
        display_name=path.rsplit(".", 1)[-1],
        query_language="sql",
        metadata_json="{}",
    )
    db_session.add(resource)
    db_session.flush()
    return resource


def identity() -> IdentityContext:
    return IdentityContext(
        user_id="user-1",
        roles=["analyst"],
    )


def test_runtime_identity_is_loaded_from_key_binding(db_session: Session) -> None:
    db_session.add(
        OrgNode(
            id="org_finance",
            name="Finance",
            code="FIN",
            parent_id=None,
            path="/finance",
            depth=0,
            status="active",
        )
    )
    db_session.add(
        User(
            id="user_1",
            name="Alice",
            external_ref="u001",
            org_node_id="org_finance",
            status="active",
        )
    )
    db_session.add(Role(id="role_finance", name="Finance"))
    db_session.add(UserRole(user_id="user_1", role_id="role_finance"))
    db_session.add(
        ApiKey(
            id="key_runtime",
            name="runtime",
            key_hash=hash_api_key("adg_runtime"),
            user_id="user_1",
            status="active",
            scopes='["runtime"]',
        )
    )
    db_session.flush()

    authenticated = authenticate_runtime_api_key_value(db_session, "adg_runtime")

    assert hasattr(authenticated, "user_id") and authenticated.user_id == "user_1"
    assert hasattr(authenticated, "role_ids") and authenticated.role_ids == ["role_finance"]
    assert (
        hasattr(authenticated, "org_node_id")
        and authenticated.org_node_id == "org_finance"
    )


def test_runtime_identity_rejects_unbound_runtime_key(db_session: Session) -> None:
    db_session.add(
        ApiKey(
            id="key_runtime",
            name="runtime",
            key_hash=hash_api_key("adg_runtime"),
            status="active",
            scopes='["runtime"]',
        )
    )
    db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        authenticate_runtime_api_key_value(db_session, "adg_runtime")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Runtime key must be bound to a user"


def test_resource_access_defaults_to_deny_when_no_policies_exist(
    db_session: Session,
) -> None:
    resource = add_resource(db_session=db_session, resource_id="res_customers")

    decision = RuntimePolicyService(db_session).check_resource_access(
        identity=identity(),
        resource=resource,
        action="read",
    )

    assert decision.allowed is False
    assert decision.reason == "no_policy_default_deny"


def test_resource_access_requires_matching_allow_when_policies_exist(
    db_session: Session,
) -> None:
    resource = add_resource(db_session=db_session, resource_id="res_customers")
    db_session.add(
        ResourcePolicy(
            subject_type="role",
            subject_id="analyst",
            effect="allow",
            action="read",
            resource_id=resource.id,
            status="active",
        )
    )

    allowed = RuntimePolicyService(db_session).check_resource_access(
        identity=identity(),
        resource=resource,
        action="read",
    )
    denied = RuntimePolicyService(db_session).check_resource_access(
        identity=IdentityContext(user_id="user-2"),
        resource=resource,
        action="read",
    )

    assert allowed.allowed is True
    assert allowed.reason == "allowed_by_policy"
    assert denied.allowed is False
    assert denied.reason == "no_matching_allow"


def test_deny_policy_overrides_allow_policy(db_session: Session) -> None:
    resource = add_resource(db_session=db_session, resource_id="res_customers")
    db_session.add_all(
        [
            ResourcePolicy(
                subject_type="role",
                subject_id="analyst",
                effect="allow",
                action="read",
                resource_id=resource.id,
                status="active",
            ),
            ResourcePolicy(
                subject_type="user",
                subject_id="user-1",
                effect="deny",
                action="read",
                resource_id=resource.id,
                status="active",
            ),
        ]
    )

    decision = RuntimePolicyService(db_session).check_resource_access(
        identity=identity(),
        resource=resource,
        action="read",
    )

    assert decision.allowed is False
    assert decision.reason == "denied_by_policy"


def test_database_allow_is_inherited_by_child_table(db_session: Session) -> None:
    database = add_resource(
        db_session=db_session,
        resource_id="res_database",
        path="warehouse",
        kind="database",
    )
    schema = add_resource(
        db_session=db_session,
        resource_id="res_schema",
        path="warehouse.public",
        parent_id=database.id,
        kind="schema",
    )
    table = add_resource(
        db_session=db_session,
        resource_id="res_table",
        path="warehouse.public.customers",
        parent_id=schema.id,
    )
    db_session.add(
        ResourcePolicy(
            subject_type="role",
            subject_id="analyst",
            effect="allow",
            action="read",
            resource_id=database.id,
            status="active",
        )
    )

    decision = RuntimePolicyService(db_session).check_resource_access(
        identity=identity(),
        resource=table,
        action="read",
    )

    assert decision.allowed is True
    assert decision.reason == "allowed_by_policy"


def test_schema_allow_is_inherited_by_child_table(db_session: Session) -> None:
    database = add_resource(
        db_session=db_session,
        resource_id="res_database",
        path="warehouse",
        kind="database",
    )
    schema = add_resource(
        db_session=db_session,
        resource_id="res_schema",
        path="warehouse.public",
        parent_id=database.id,
        kind="schema",
    )
    table = add_resource(
        db_session=db_session,
        resource_id="res_table",
        path="warehouse.public.customers",
        parent_id=schema.id,
    )
    db_session.add(
        ResourcePolicy(
            subject_type="role",
            subject_id="analyst",
            effect="allow",
            action="read",
            resource_id=schema.id,
            status="active",
        )
    )

    decision = RuntimePolicyService(db_session).check_resource_access(
        identity=identity(),
        resource=table,
        action="read",
    )

    assert decision.allowed is True
    assert decision.reason == "allowed_by_policy"


def test_table_deny_overrides_database_allow(db_session: Session) -> None:
    database = add_resource(
        db_session=db_session,
        resource_id="res_database",
        path="warehouse",
        kind="database",
    )
    schema = add_resource(
        db_session=db_session,
        resource_id="res_schema",
        path="warehouse.public",
        parent_id=database.id,
        kind="schema",
    )
    table = add_resource(
        db_session=db_session,
        resource_id="res_table",
        path="warehouse.public.customers",
        parent_id=schema.id,
    )
    db_session.add_all(
        [
            ResourcePolicy(
                subject_type="role",
                subject_id="analyst",
                effect="allow",
                action="read",
                resource_id=database.id,
                status="active",
            ),
            ResourcePolicy(
                subject_type="user",
                subject_id="user-1",
                effect="deny",
                action="read",
                resource_id=table.id,
                status="active",
            ),
        ]
    )

    decision = RuntimePolicyService(db_session).check_resource_access(
        identity=identity(),
        resource=table,
        action="read",
    )

    assert decision.allowed is False
    assert decision.reason == "denied_by_policy"


def test_legacy_group_tag_policy_does_not_match_runtime_identity(
    db_session: Session,
) -> None:
    resource = add_resource(db_session=db_session, resource_id="res_customers")
    tag = Tag(id="tag_pii", name="pii", category="classification")
    db_session.add(tag)
    db_session.add(ResourceTag(tag_id=tag.id, resource_id=resource.id))
    db_session.add(
        ResourcePolicy(
            subject_type="group",
            subject_id="finance",
            effect="deny",
            action="read",
            tag_id=tag.id,
            status="active",
        )
    )

    decision = RuntimePolicyService(db_session).check_resource_access(
        identity=identity(),
        resource=resource,
        action="read",
    )

    assert decision.allowed is False
    assert decision.reason == "no_matching_allow"


def test_field_policy_can_narrow_resource_access(db_session: Session) -> None:
    resource = add_resource(db_session=db_session, resource_id="res_customers")
    db_session.add(
        ResourcePolicy(
            subject_type="role",
            subject_id="analyst",
            effect="allow",
            action="read",
            resource_id=resource.id,
            status="active",
        )
    )
    db_session.add(
        FieldPolicy(
            subject_type="all",
            subject_id="*",
            effect="deny",
            resource_id=resource.id,
            field_name="email",
            action="read",
            status="active",
        )
    )

    service = RuntimePolicyService(db_session)

    assert (
        service.check_field_access(
            identity=identity(),
            resource=resource,
            field_name="email",
            action="read",
        ).allowed
        is False
    )
    assert (
        service.check_field_access(
            identity=identity(),
            resource=resource,
            field_name="name",
            action="read",
        ).allowed
        is True
    )


def test_decrypt_access_requires_explicit_allow_decrypt_flag(db_session: Session) -> None:
    resource = add_resource(db_session=db_session, resource_id="res_customers")
    db_session.add(
        ResourcePolicy(
            subject_type="role",
            subject_id="analyst",
            effect="allow",
            action="read",
            resource_id=resource.id,
            allow_decrypt=False,
            status="active",
        )
    )

    denied = RuntimePolicyService(db_session).check_decrypt_access(
        identity=identity(),
        resource=resource,
    )

    assert denied.allowed is False
    assert denied.reason == "decrypt_not_allowed"

    db_session.add(
        ResourcePolicy(
            subject_type="user",
            subject_id="user-1",
            effect="allow",
            action="read",
            resource_id=resource.id,
            allow_decrypt=True,
            status="active",
        )
    )

    allowed = RuntimePolicyService(db_session).check_decrypt_access(
        identity=identity(),
        resource=resource,
    )

    assert allowed.allowed is True
    assert allowed.reason == "allowed_by_policy"
