from sqlalchemy.orm import Session

from adg.control_plane.models.governance import FieldPolicy, ResourcePolicy, ResourceTag, Tag
from adg.control_plane.models.resource import Resource
from adg.policy.runtime import IdentityContext, RuntimePolicyService


def add_resource(
    *,
    db_session: Session,
    resource_id: str,
    datasource_id: str = "ds_1",
    path: str = "warehouse.public.customers",
) -> Resource:
    resource = Resource(
        id=resource_id,
        datasource_id=datasource_id,
        parent_id=None,
        kind="relational_table",
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
        groups=["finance"],
    )


def test_resource_access_defaults_to_allow_when_no_policies_exist(
    db_session: Session,
) -> None:
    resource = add_resource(db_session=db_session, resource_id="res_customers")

    decision = RuntimePolicyService(db_session).check_resource_access(
        identity=identity(),
        resource=resource,
        action="read",
    )

    assert decision.allowed is True
    assert decision.reason == "no_policy"


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


def test_tag_policy_matches_attached_resource_tag(db_session: Session) -> None:
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
    assert decision.reason == "denied_by_policy"


def test_field_policy_can_narrow_resource_access(db_session: Session) -> None:
    resource = add_resource(db_session=db_session, resource_id="res_customers")
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
